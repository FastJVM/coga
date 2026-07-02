"""Per-agent subscription usage-window probes and the drain budget guard.

The drain (megalaunch) decides "is there enough budget to start another
ticket?" by reading each agent's **own** subscription usage windows — the
5h/session window and the weekly window — instead of coga tracking tokens
itself. One probe implementation exists per agent CLI:

- **claude** — a free, fresh read: `GET https://api.anthropic.com/api/oauth/usage`
  with the OAuth bearer token from `~/.claude/.credentials.json`. The response
  reports the subscription window (`five_hour.utilization`,
  `seven_day.utilization` as percent-used, plus reset times), not per-minute
  rate-limit headers. Costs no tokens. (macOS keeps the credentials in the
  Keychain rather than this file; the drain targets Linux/headless machines,
  where the file path holds.)

- **codex** — no free fresh endpoint exists (the ChatGPT-backend usage GETs
  are Cloudflare-blocked). Codex only emits its window data as a
  `rate_limits` snapshot attached to a real model call, persisted into
  `~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl`. So the probe primes once
  per drain with a minimal throwaway `codex exec`, then reads the newest
  rollout snapshot written after the primer started. Each subsequent codex
  launch rewrites the snapshot, so later re-reads stay fresh for free.

Every probe **fails soft**: any error, timeout, missing file, or stale
snapshot returns ``None`` ("no budget signal"), and the caller conservatively
skips that agent's drain. A probe must never crash the sweep.

The guard (`budget_allows_launch`) applies two reserves from `[megalaunch]`
config: a fixed session floor, and a weekly *pacing* reserve that requires
~100% remaining at the start of the weekly window and relaxes linearly down
to the hard floor inside the final `weekly_final_window_hours` — so leftover
allotment is spent aggressively just before reset but never exhausted early
in the week.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from coga.config import Config, MegalaunchConfig

CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
PROBE_TIMEOUT_SECONDS = 15.0
CODEX_PRIMER_TIMEOUT_SECONDS = 180.0
WEEKLY_WINDOW_HOURS = 168.0


@dataclass(frozen=True)
class UsageWindow:
    """One usage window: percent already used, and when it resets."""

    used_percent: float
    resets_at: datetime | None

    @property
    def remaining_percent(self) -> float:
        return max(0.0, 100.0 - self.used_percent)


@dataclass(frozen=True)
class UsageSnapshot:
    """An agent's session (5h) and weekly windows, read at one moment."""

    agent: str
    session: UsageWindow
    weekly: UsageWindow


@dataclass(frozen=True)
class BudgetDecision:
    """The guard's verdict for one agent, with a human-readable reason."""

    allowed: bool
    detail: str
    snapshot: UsageSnapshot | None = None


class UsageProbe:
    """Reads one agent's current usage windows. Implementations fail soft."""

    def read(self) -> UsageSnapshot | None:
        raise NotImplementedError


class ClaudeUsageProbe(UsageProbe):
    """Live OAuth usage read — free, fresh, no tokens spent."""

    def __init__(self, agent: str, credentials_path: Path | None = None) -> None:
        self.agent = agent
        self.credentials_path = (
            credentials_path or Path.home() / ".claude" / ".credentials.json"
        )

    def read(self) -> UsageSnapshot | None:
        # Fail soft on anything — missing/garbled credentials, network errors,
        # HTTP failures, unexpected response shapes. "No signal" means the
        # caller skips this agent; it must never crash the sweep.
        try:
            creds = json.loads(self.credentials_path.read_text())
            token = creds["claudeAiOauth"]["accessToken"]
            response = requests.get(
                CLAUDE_USAGE_URL,
                headers={"Authorization": f"Bearer {token}"},
                timeout=PROBE_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
            session = _window_from_oauth(body["five_hour"])
            weekly = _window_from_oauth(body["seven_day"])
        except Exception:
            return None
        return UsageSnapshot(agent=self.agent, session=session, weekly=weekly)


class CodexUsageProbe(UsageProbe):
    """Prime-once `codex exec` + freshness-guarded rollout snapshot read."""

    def __init__(self, agent: str, codex_home: Path | None = None) -> None:
        self.agent = agent
        self.codex_home = codex_home or Path.home() / ".codex"
        self._primed_at: datetime | None = None

    def read(self) -> UsageSnapshot | None:
        if self._primed_at is None and not self._prime():
            return None
        return self._newest_snapshot()

    def _prime(self) -> bool:
        """Fire one minimal throwaway exec so codex persists a fresh snapshot."""
        started_at = datetime.now(timezone.utc)
        try:
            # stdin must be closed or codex blocks on "Reading additional
            # input from stdin...". The read-only sandbox keeps the throwaway
            # contained; it costs a few thousand mostly-cached input tokens.
            result = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--json",
                    "-s",
                    "read-only",
                    "--skip-git-repo-check",
                    "Reply with exactly: ok",
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=CODEX_PRIMER_TIMEOUT_SECONDS,
            )
        except Exception:
            return False
        if result.returncode != 0:
            return False
        self._primed_at = started_at
        return True

    def _newest_snapshot(self) -> UsageSnapshot | None:
        """Read `rate_limits` from the newest rollout written since priming.

        The `--json` event stream does NOT carry rate_limits — only the
        persisted rollout file does. A file older than the primer is a stale
        snapshot from some earlier run and is rejected (no signal) rather
        than trusted.
        """
        try:
            primed_ts = (self._primed_at or datetime.now(timezone.utc)).timestamp()
            candidates = sorted(
                (
                    path
                    for path in (self.codex_home / "sessions").rglob("rollout-*.jsonl")
                    if path.stat().st_mtime >= primed_ts
                ),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            for path in candidates:
                limits = _last_rate_limits(path)
                if limits is None:
                    continue
                return UsageSnapshot(
                    agent=self.agent,
                    session=_window_from_rate_limit(limits["primary"]),
                    weekly=_window_from_rate_limit(limits["secondary"]),
                )
        except Exception:
            return None
        return None


def _window_from_oauth(raw: dict) -> UsageWindow:
    """Parse one window from the Anthropic OAuth usage body."""
    return UsageWindow(
        used_percent=float(raw["utilization"]),
        resets_at=_parse_iso_ts(raw.get("resets_at")),
    )


def _window_from_rate_limit(raw: dict) -> UsageWindow:
    """Parse one window from a codex rollout `rate_limits` entry."""
    resets_at = raw.get("resets_at")
    return UsageWindow(
        used_percent=float(raw["used_percent"]),
        resets_at=(
            datetime.fromtimestamp(resets_at, tz=timezone.utc)
            if isinstance(resets_at, (int, float)) and not isinstance(resets_at, bool)
            else None
        ),
    )


def _parse_iso_ts(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _last_rate_limits(path: Path) -> dict | None:
    """Find the last parseable `rate_limits` object in a rollout JSONL file."""
    for line in reversed(path.read_text().splitlines()):
        if '"rate_limits"' not in line:
            continue
        try:
            found = _find_key(json.loads(line), "rate_limits")
        except json.JSONDecodeError:
            continue
        if isinstance(found, dict) and "primary" in found and "secondary" in found:
            return found
    return None


def _find_key(obj: object, key: str) -> object | None:
    """Depth-first search for `key` — rollout nesting is not a stable API."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_key(value, key)
            if found is not None:
                return found
    return None


def build_probes(cfg: Config) -> dict[str, UsageProbe]:
    """One probe per configured agent, keyed by agent name, chosen by CLI.

    An agent whose CLI has no probe implementation gets no entry — the guard
    treats that as "no budget signal" and skips it conservatively.
    """
    probes: dict[str, UsageProbe] = {}
    for name, agent in cfg.agents.items():
        cli = Path(agent.cli).name
        if cli == "claude":
            probes[name] = ClaudeUsageProbe(name)
        elif cli == "codex":
            probes[name] = CodexUsageProbe(name)
    return probes


def weekly_required_remaining_percent(
    mcfg: MegalaunchConfig, hours_to_reset: float
) -> float:
    """The weekly pacing reserve: how much must remain, given time to reset.

    Linear from 100% required at a full window out, down to the hard floor
    (`min_weekly_remaining_percent`) inside the final
    `weekly_final_window_hours`. Never below the floor, so the drain still
    cannot exhaust the account on the last day.
    """
    floor = mcfg.min_weekly_remaining_percent
    final = mcfg.weekly_final_window_hours
    if hours_to_reset <= final:
        return floor
    span = max(WEEKLY_WINDOW_HOURS - final, 1e-9)
    fraction = min(1.0, (hours_to_reset - final) / span)
    return floor + (100.0 - floor) * fraction


def budget_allows_launch(
    snapshot: UsageSnapshot,
    mcfg: MegalaunchConfig,
    *,
    now: datetime | None = None,
) -> BudgetDecision:
    """Apply the session floor and the weekly pacing reserve to one snapshot."""
    now = now or datetime.now(timezone.utc)
    session_remaining = snapshot.session.remaining_percent
    if session_remaining < mcfg.min_session_remaining_percent:
        return BudgetDecision(
            False,
            f"session window {session_remaining:.1f}% remaining is below the "
            f"{mcfg.min_session_remaining_percent:.1f}% reserve",
            snapshot,
        )
    if snapshot.weekly.resets_at is None:
        return BudgetDecision(
            False,
            "weekly window carries no reset time; treated as no budget signal",
            snapshot,
        )
    hours_to_reset = max(0.0, (snapshot.weekly.resets_at - now).total_seconds() / 3600)
    required = weekly_required_remaining_percent(mcfg, hours_to_reset)
    weekly_remaining = snapshot.weekly.remaining_percent
    if weekly_remaining < required:
        return BudgetDecision(
            False,
            f"weekly window {weekly_remaining:.1f}% remaining is below the "
            f"{required:.1f}% pacing reserve ({hours_to_reset:.0f}h to reset)",
            snapshot,
        )
    return BudgetDecision(
        True,
        f"session {session_remaining:.1f}% / weekly {weekly_remaining:.1f}% remaining",
        snapshot,
    )


def check_budget(
    probes: dict[str, UsageProbe],
    agent: str | None,
    mcfg: MegalaunchConfig,
    *,
    now: datetime | None = None,
) -> BudgetDecision:
    """Probe one agent and apply the guard. No probe / no signal → not allowed."""
    agent_name = agent or ""
    probe = probes.get(agent_name)
    if probe is None:
        return BudgetDecision(
            False, f"no usage probe for agent {agent_name!r}; skipped conservatively"
        )
    snapshot = probe.read()
    if snapshot is None:
        return BudgetDecision(
            False,
            f"usage window unreadable for agent {agent_name!r}; skipped conservatively",
        )
    return budget_allows_launch(snapshot, mcfg, now=now)


__all__ = [
    "BudgetDecision",
    "ClaudeUsageProbe",
    "CodexUsageProbe",
    "UsageProbe",
    "UsageSnapshot",
    "UsageWindow",
    "budget_allows_launch",
    "build_probes",
    "check_budget",
    "weekly_required_remaining_percent",
]
