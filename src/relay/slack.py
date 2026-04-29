"""Slack webhook poster.

When a webhook is configured (via `[slack] webhook` in relay.toml or the
`$SLACK_WEBHOOK_URL` env-var fallback), every call POSTs JSON `{text: ...}`.
Otherwise messages are written to stderr prefixed with `[slack]` so dev/test
runs still surface the traffic.

On a `RequestException`, the post is retried with exponential backoff
(see `_RETRY_DELAYS`). If all retries exhaust, a structured record is
appended to `<repo_root>/.slack-failures.log` so scripted runs can tell
that posts didn't land.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from relay.config import Config

FAILURES_LOG = ".slack-failures.log"
_MESSAGE_PREVIEW_MAX = 120
_RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0)


def post(cfg: Config, message: str) -> None:
    """Post a message to the configured Slack channel (or stderr fallback)."""
    if not cfg.slack_webhook:
        sys.stderr.write(f"[slack] {message}\n")
        return

    last_exc: requests.RequestException | None = None
    for attempt, delay in enumerate((0.0, *_RETRY_DELAYS)):
        if delay > 0:
            time.sleep(delay)
        try:
            requests.post(
                cfg.slack_webhook,
                json={"text": message},
                timeout=5,
            )
            return
        except requests.RequestException as exc:
            last_exc = exc

    assert last_exc is not None  # the loop ran at least once
    sys.stderr.write(f"[slack] post failed: {last_exc}. Message was: {message}\n")
    _record_failure(cfg.repo_root, message, last_exc)


def _record_failure(repo_root: Path, message: str, exc: BaseException) -> None:
    """Append a tab-separated failure record to <repo_root>/.slack-failures.log."""
    line = "\t".join((
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        type(exc).__name__,
        message[:_MESSAGE_PREVIEW_MAX].replace("\t", " ").replace("\n", " "),
    ))
    try:
        with (repo_root / FAILURES_LOG).open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as write_exc:
        sys.stderr.write(f"[slack] could not record failure: {write_exc}\n")


__all__ = ["post", "FAILURES_LOG"]
