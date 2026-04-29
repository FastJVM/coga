"""Slack webhook poster.

When a webhook is configured (via `[slack] webhook` in relay.toml or the
`$SLACK_WEBHOOK_URL` env-var fallback), every call POSTs JSON `{text: ...}`.
Otherwise messages are written to stderr prefixed with `[slack]` so dev/test
runs still surface the traffic.

On failure, the error goes to stderr (the human at the terminal sees it).
When called with a `task_path`, the failure is also appended to that task's
`log.md` — so daemon / scheduled / scripted runs leave a durable record
even when nobody's watching stderr.
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

from relay.config import Config
from relay.logfile import append_log


def post(cfg: Config, message: str, *, task_path: Path | None = None) -> None:
    """Post a message to the configured Slack channel (or stderr fallback)."""
    if not cfg.slack_webhook:
        sys.stderr.write(f"[slack] {message}\n")
        return
    try:
        requests.post(
            cfg.slack_webhook,
            json={"text": message},
            timeout=5,
        )
    except requests.RequestException as exc:
        sys.stderr.write(f"[slack] post failed: {exc}. Message was: {message}\n")
        if task_path is not None:
            append_log(task_path, "slack", f"post failed: {type(exc).__name__}: {exc}")


__all__ = ["post"]
