"""Anonymous install telemetry — the opt-out, no-PII product-market-fit ping.

A single daily ping that answers three PM questions: how many real installs
exist, whether they're used (any tickets), and whether they're still active
(recent run). It carries **exactly** three fields and nothing else:

    {"instance_id": "<uuid4>", "tickets_total": 12, "last_run": "2026-06-19"}

Nothing here runs in the foreground dispatch path. The send is driven by the
daily `coga/recurring/telemetry/` recurring task (a `mode: script` step), so
the recurring period owns the once-per-day cadence and idempotency — there is
no throttle file and no `main()` hook.

Privacy invariants enforced by this module:

- The only stable identifier is a random UUIDv4 stored in machine-local state
  (`$XDG_STATE_HOME/coga/instance-id`), generated once and never derived from
  machine, user, or repo identity.
- `tickets_total` is a bare count of `ticket.md` files — no status, slug,
  title, or content.
- `last_run` is a coarse UTC date, no finer timestamp.
- No repo path, cwd, hostname, username, git remote, or ticket text is read.

On by default (opt-out). Three independent disable paths, any of which wins:
`[telemetry] enabled = false` in config, `COGA_TELEMETRY_DISABLE=1`, or the
cross-tool standard `DO_NOT_TRACK=1`. Env always beats config, and disable
always wins (env can only force the ping off, never on).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from coga import tasks
from coga.atomicio import atomic_write_text
from coga.config import Config

# Endpoint the ping POSTs to. This is a placeholder until the owner runs
# `telemetry-endpoint/deploy.sh` and pins the printed URL here; the `.invalid`
# TLD never resolves, so until then every send fails fast and silently (which
# is the correct fail-open-for-the-user behavior). Override at runtime with
# `COGA_TELEMETRY_URL` to point at a test relay.
TELEMETRY_URL = "https://coga-telemetry.invalid/ping"

_URL_ENV = "COGA_TELEMETRY_URL"
_DISABLE_ENV = "COGA_TELEMETRY_DISABLE"
_DO_NOT_TRACK_ENV = "DO_NOT_TRACK"

# How long to wait on the network before giving up. Mirrors the 5s timeout the
# Slack sender uses (`notification/slack.py`); the ping is best-effort and must
# never hold anything up.
_TIMEOUT_SECONDS = 5


def machine_state_dir() -> Path:
    """Machine-local state directory: `$XDG_STATE_HOME/coga`.

    Falls back to `~/.local/state/coga` per the XDG Base Directory spec. This
    is the one Coga path that is deliberately **not** repo-relative — the
    install identity must persist across every repo on the machine, so it lives
    in the user's state dir, never in a `coga/` tree. (Everything in
    `coga.paths` is repo-relative by contract; this stays here for that reason.)
    """
    xdg_state = os.environ.get("XDG_STATE_HOME", "").strip()
    base = Path(xdg_state) if xdg_state else Path.home() / ".local" / "state"
    return base / "coga"


def instance_id_path() -> Path:
    """Path to the machine-local install identifier file."""
    return machine_state_dir() / "instance-id"


def read_or_create_instance_id() -> str:
    """Return this install's UUIDv4, generating and persisting it on first read.

    The id is the only join key the telemetry carries. It is random — not
    derived from anything — and machine-local, so it counts distinct installs
    without identifying any of them. Written atomically; concurrent first reads
    converge because each writes a valid uuid4 and the last writer wins
    (whichever uuid survives, it's still one anonymous install).
    """
    path = instance_id_path()
    try:
        existing = path.read_text().strip()
    except OSError:
        existing = ""
    if existing:
        return existing
    new_id = str(uuid.uuid4())
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, new_id + "\n")
    return new_id


def build_payload(cfg: Config) -> dict[str, object]:
    """Build the exact wire payload: `instance_id`, `tickets_total`, `last_run`.

    These three keys are the entire payload — see the module docstring for why
    nothing else may join them. `tickets_total` counts `ticket.md` files only
    (via `tasks.list_tasks`); `last_run` is today's UTC date, which is the most
    recent run by construction (the ping fires only when the recurring sweep
    runs).
    """
    return {
        "instance_id": read_or_create_instance_id(),
        "tickets_total": len(tasks.list_tasks(cfg)),
        "last_run": datetime.now(timezone.utc).date().isoformat(),
    }


def telemetry_url() -> str:
    """The endpoint to POST to: `COGA_TELEMETRY_URL` override, else the constant."""
    return os.environ.get(_URL_ENV, "").strip() or TELEMETRY_URL


def _env_truthy(name: str) -> bool:
    """True when env var `name` is set to anything other than a falsy literal."""
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() not in ("", "0", "false", "no", "off")


def disabled_reason(cfg: Config) -> str | None:
    """Why telemetry is off, or `None` when it is on.

    Precedence — env beats config, and any disable wins:
    1. `DO_NOT_TRACK` truthy (cross-tool standard),
    2. `COGA_TELEMETRY_DISABLE` truthy (Coga's own kill switch),
    3. `[telemetry] enabled = false` in config.
    """
    if _env_truthy(_DO_NOT_TRACK_ENV):
        return f"{_DO_NOT_TRACK_ENV} is set"
    if _env_truthy(_DISABLE_ENV):
        return f"{_DISABLE_ENV} is set"
    if not cfg.telemetry_enabled:
        return "[telemetry] enabled = false in config"
    return None


def telemetry_disabled(cfg: Config) -> bool:
    """True when no ping should be sent (any disable path active)."""
    return disabled_reason(cfg) is not None


@dataclass(frozen=True)
class SendResult:
    """Outcome of a `send` attempt — what the recurring script records.

    `sent` is True only on a real 2xx. `skipped` means telemetry was disabled
    (no network call). `detail` is a one-line, human-legible summary for the
    task blackboard / `coga telemetry show`.
    """

    sent: bool
    skipped: bool
    detail: str


def send(cfg: Config) -> SendResult:
    """Send one ping, or skip when disabled. Never raises.

    The contract the recurring task relies on: a failure is **returned** (for
    the caller to record), never raised — the daily run must not crash on a
    flaky network or a not-yet-deployed endpoint. A skip is a clean no-op with
    zero network calls.
    """
    reason = disabled_reason(cfg)
    if reason is not None:
        return SendResult(sent=False, skipped=True, detail=f"skipped — {reason}")

    url = telemetry_url()
    try:
        payload = build_payload(cfg)
    except Exception as exc:  # building the payload must not crash the run
        return SendResult(sent=False, skipped=False, detail=f"payload error: {exc}")

    try:
        resp = requests.post(url, json=payload, timeout=_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return SendResult(
            sent=False, skipped=False, detail=f"network error: {exc}"
        )

    if 200 <= resp.status_code < 300:
        return SendResult(sent=True, skipped=False, detail=f"sent ({resp.status_code})")
    return SendResult(
        sent=False, skipped=False, detail=f"non-2xx response: {resp.status_code}"
    )


__all__ = [
    "TELEMETRY_URL",
    "SendResult",
    "build_payload",
    "disabled_reason",
    "instance_id_path",
    "machine_state_dir",
    "read_or_create_instance_id",
    "send",
    "telemetry_disabled",
    "telemetry_url",
]
