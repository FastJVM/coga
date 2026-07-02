from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent

import pytest

from coga.config import MegalaunchConfig, load_config
from coga.usage_probe import (
    ClaudeUsageProbe,
    CodexUsageProbe,
    UsageProbe,
    UsageSnapshot,
    UsageWindow,
    budget_allows_launch,
    build_probes,
    check_budget,
    weekly_required_remaining_percent,
)

NOW = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def _snapshot(
    session_used: float = 0.0,
    weekly_used: float = 0.0,
    weekly_resets_in_hours: float | None = 1.0,
) -> UsageSnapshot:
    return UsageSnapshot(
        agent="claude",
        session=UsageWindow(session_used, NOW + timedelta(hours=5)),
        weekly=UsageWindow(
            weekly_used,
            None
            if weekly_resets_in_hours is None
            else NOW + timedelta(hours=weekly_resets_in_hours),
        ),
    )


# --- Claude probe ---


class _FakeResponse:
    def __init__(self, body: dict) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._body


def _write_credentials(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"claudeAiOauth": {"accessToken": "tok-123"}}))


def test_claude_probe_parses_subscription_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    creds = tmp_path / ".credentials.json"
    _write_credentials(creds)
    seen: dict[str, object] = {}

    def fake_get(url, headers=None, timeout=None):  # type: ignore[no-untyped-def]
        seen["url"] = url
        seen["headers"] = headers
        return _FakeResponse({
            "five_hour": {"utilization": 2.0, "resets_at": "2026-07-01T14:00:00Z"},
            "seven_day": {"utilization": 40.0, "resets_at": "2026-07-03T00:00:00+00:00"},
        })

    monkeypatch.setattr("coga.usage_probe.requests.get", fake_get)

    snapshot = ClaudeUsageProbe("claude", credentials_path=creds).read()

    assert snapshot is not None
    assert snapshot.session.used_percent == 2.0
    assert snapshot.session.remaining_percent == 98.0
    assert snapshot.weekly.used_percent == 40.0
    assert snapshot.weekly.resets_at == datetime(2026, 7, 3, tzinfo=timezone.utc)
    assert seen["url"] == "https://api.anthropic.com/api/oauth/usage"
    assert seen["headers"] == {"Authorization": "Bearer tok-123"}


def test_claude_probe_missing_credentials_fails_soft(tmp_path: Path) -> None:
    probe = ClaudeUsageProbe("claude", credentials_path=tmp_path / "absent.json")

    assert probe.read() is None


def test_claude_probe_network_error_fails_soft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    creds = tmp_path / ".credentials.json"
    _write_credentials(creds)

    def fake_get(url, headers=None, timeout=None):  # type: ignore[no-untyped-def]
        raise OSError("network down")

    monkeypatch.setattr("coga.usage_probe.requests.get", fake_get)

    assert ClaudeUsageProbe("claude", credentials_path=creds).read() is None


# --- Codex probe ---


_RATE_LIMITS = {
    "primary": {"used_percent": 1.0, "window_minutes": 300, "resets_at": 1782909000},
    "secondary": {"used_percent": 6.0, "window_minutes": 10080, "resets_at": 1783200000},
}


def _write_rollout(
    codex_home: Path, name: str, payload: dict, mtime: float | None = None
) -> Path:
    day = codex_home / "sessions" / "2026" / "07" / "01"
    day.mkdir(parents=True, exist_ok=True)
    path = day / name
    path.write_text(json.dumps(payload) + "\n")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_codex_probe_primes_then_reads_fresh_rollout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / ".codex"
    primer_argv: list[list[str]] = []

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        primer_argv.append(argv)
        # The primer's model call persists a fresh rollout snapshot; the
        # rate_limits sit nested in an event payload, not at the top level.
        _write_rollout(
            codex_home, "rollout-fresh.jsonl", {"payload": {"rate_limits": _RATE_LIMITS}}
        )
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr("coga.usage_probe.subprocess.run", fake_run)

    snapshot = CodexUsageProbe("codex", codex_home=codex_home).read()

    assert snapshot is not None
    assert snapshot.session.used_percent == 1.0
    assert snapshot.weekly.used_percent == 6.0
    assert snapshot.weekly.resets_at == datetime.fromtimestamp(
        1783200000, tz=timezone.utc
    )
    assert primer_argv and primer_argv[0][:2] == ["codex", "exec"]


def test_codex_probe_rejects_stale_rollout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / ".codex"
    # A snapshot from some earlier run, hours before the primer fires.
    _write_rollout(
        codex_home,
        "rollout-stale.jsonl",
        {"payload": {"rate_limits": _RATE_LIMITS}},
        mtime=datetime.now(timezone.utc).timestamp() - 3600,
    )
    monkeypatch.setattr(
        "coga.usage_probe.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, b"", b""),
    )

    assert CodexUsageProbe("codex", codex_home=codex_home).read() is None


def test_codex_probe_primer_failure_fails_soft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setattr(
        "coga.usage_probe.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1, b"", b"boom"),
    )

    assert CodexUsageProbe("codex", codex_home=codex_home).read() is None


def test_codex_probe_missing_cli_fails_soft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("codex")

    monkeypatch.setattr("coga.usage_probe.subprocess.run", fake_run)

    assert CodexUsageProbe("codex", codex_home=tmp_path / ".codex").read() is None


def test_codex_probe_primes_once_across_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / ".codex"
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(argv)
        _write_rollout(
            codex_home, "rollout-fresh.jsonl", {"payload": {"rate_limits": _RATE_LIMITS}}
        )
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr("coga.usage_probe.subprocess.run", fake_run)
    probe = CodexUsageProbe("codex", codex_home=codex_home)

    assert probe.read() is not None
    assert probe.read() is not None
    # One throwaway exec per drain; later reads reuse the rollout snapshots
    # the drain's own codex launches keep rewriting.
    assert len(calls) == 1


# --- The guard ---


def test_weekly_pacing_reserve_is_linear_down_to_the_floor() -> None:
    mcfg = MegalaunchConfig()

    assert weekly_required_remaining_percent(mcfg, 168.0) == 100.0
    # ~84% required six days out, per the reviewed pacing table.
    assert weekly_required_remaining_percent(mcfg, 144.0) == pytest.approx(84.2, abs=0.1)
    assert weekly_required_remaining_percent(mcfg, 24.0) == 5.0
    assert weekly_required_remaining_percent(mcfg, 1.0) == 5.0
    # Clamped: a reset further out than one window never demands >100%.
    assert weekly_required_remaining_percent(mcfg, 500.0) == 100.0


def test_session_reserve_blocks_launch() -> None:
    decision = budget_allows_launch(
        _snapshot(session_used=96.0), MegalaunchConfig(), now=NOW
    )

    assert not decision.allowed
    assert "session" in decision.detail


def test_weekly_pacing_blocks_early_week_spend() -> None:
    # Three days to reset requires ~36.7% remaining; only 30% is left.
    decision = budget_allows_launch(
        _snapshot(weekly_used=70.0, weekly_resets_in_hours=72.0),
        MegalaunchConfig(),
        now=NOW,
    )

    assert not decision.allowed
    assert "weekly" in decision.detail


def test_weekly_final_window_allows_aggressive_spend() -> None:
    # Inside the final 24h only the hard floor applies: 10% remaining is fine.
    decision = budget_allows_launch(
        _snapshot(weekly_used=90.0, weekly_resets_in_hours=12.0),
        MegalaunchConfig(),
        now=NOW,
    )

    assert decision.allowed


def test_missing_weekly_reset_time_blocks() -> None:
    decision = budget_allows_launch(
        _snapshot(weekly_resets_in_hours=None), MegalaunchConfig(), now=NOW
    )

    assert not decision.allowed
    assert "no budget signal" in decision.detail


def test_check_budget_without_probe_skips_conservatively() -> None:
    decision = check_budget({}, "claude", MegalaunchConfig())

    assert not decision.allowed
    assert "no usage probe" in decision.detail


def test_check_budget_unreadable_probe_skips_conservatively() -> None:
    class _NoSignal(UsageProbe):
        def read(self) -> UsageSnapshot | None:
            return None

    decision = check_budget({"claude": _NoSignal()}, "claude", MegalaunchConfig())

    assert not decision.allowed
    assert "unreadable" in decision.detail


# --- Probe registry ---


def test_build_probes_maps_agents_by_cli(tmp_path: Path) -> None:
    company = tmp_path / "coga"
    company.mkdir()
    (company / "coga.toml").write_text(
        dedent(
            """
            version = 1
            [agents.claude]
            cli = "claude"
            auto = "-p"
            file = "CLAUDE.md"
            [agents.codex]
            cli = "codex"
            auto = "exec"
            file = "AGENTS.md"
            [agents.exotic]
            cli = "exotic-cli"
            auto = "-p"
            file = "AGENTS.md"
            """
        ).lstrip()
    )
    (company / "coga.local.toml").write_text('user = "marc"\n')
    cfg = load_config(company)

    probes = build_probes(cfg)

    assert isinstance(probes["claude"], ClaudeUsageProbe)
    assert isinstance(probes["codex"], CodexUsageProbe)
    # No probe implementation → no entry → the guard skips it conservatively.
    assert "exotic" not in probes
