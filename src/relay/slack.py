"""Slack webhook poster — relay's sync point with humans.

Slack is required by default for multi-user coordination: agents and CLI
commands post here so teammates see state changes as they happen. A silent
FYI becomes a stale mental model on the human side, so failures crash
loudly rather than degrade.

Three branches:
  - `slack_enabled = False` (opt-out via `[slack].enabled = false` in
    `relay.local.toml`) — every call writes to stderr, never crashes. The
    cost is being out of the sync loop.
  - `enabled` + no webhook — crash with a message pointing the user at
    `$SLACK_WEBHOOK_URL` and the opt-out.
  - `enabled` + webhook — POST. On any RequestException, append to the
    task's `log.md` (when `task_path` is given) and crash so the caller
    sees the failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests
import typer

from relay.config import Config
from relay.logfile import append_log


def post(
    cfg: Config,
    message: str,
    *,
    task_path: Path | None = None,
    image_url: str | None = None,
) -> None:
    """Post a message to Slack, or crash trying.

    `image_url`, if given, attaches a single image (GIF or PNG) below the
    text via Slack's `attachments` field — used for milestone events
    (done, panic) so they pop visually in a high-volume feed.

    See module docstring for the three branches and why we crash.
    """
    if not cfg.slack_enabled:
        sys.stderr.write(f"[slack] disabled (post suppressed): {message}\n")
        return

    if not cfg.slack_webhook:
        sys.stderr.write(
            "[slack] $SLACK_WEBHOOK_URL is not set. "
            "Export it, or opt out with [slack].enabled = false in relay.local.toml.\n"
        )
        raise typer.Exit(1)

    payload: dict[str, object] = {"text": message}
    if image_url:
        payload["attachments"] = [{"image_url": image_url, "fallback": message}]

    try:
        requests.post(
            cfg.slack_webhook,
            json=payload,
            timeout=5,
        )
    except requests.RequestException as exc:
        sys.stderr.write(f"[slack] post failed: {exc}. Message was: {message}\n")
        if task_path is not None:
            append_log(task_path, "slack", f"post failed: {type(exc).__name__}: {exc}")
        raise typer.Exit(1)


__all__ = ["post"]
