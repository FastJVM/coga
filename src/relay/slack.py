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


def _mention(cfg: Config, name: str) -> str:
    """Render `name` as a Slack ping when its member ID is mapped.

    `[slack.users]` in `relay.toml` maps a relay name to a Slack member ID.
    Slack only fires a notification for the `<@U…>` mention form, so a
    mapped name becomes `<@U…>`; an unmapped one stays plain text (named,
    but not pinged). An incoming webhook can't resolve an ID itself — that's
    why the table has to be supplied.
    """
    user_id = cfg.slack_users.get(name)
    return f"<@{user_id}>" if user_id else name


def post(
    cfg: Config,
    message: str,
    *,
    task_path: Path | None = None,
    owner: str | None = None,
    watchers: list[str] | None = None,
    image_url: str | None = None,
) -> None:
    """Post a message to Slack, or crash trying.

    Every message is prefixed with `[<project>]` so a Slack channel shared
    across multiple relay repos stays disambiguated. When `owner` is given,
    `[<owner>]` follows — that's the human accountable for the ticket, so
    teammates can tell whose agent (e.g. `claude`) just acted when several
    teammates share an agent nickname. Owner and watchers render as real
    `<@ID>` pings for any name mapped in `[slack.users]` (see `_mention`).

    `watchers`, if given, are cc'd in a trailer — but only those with a
    mapped member ID, since cc'ing a plain name notifies no one and is just
    noise.

    `image_url`, if given, attaches a single image (GIF or PNG) below the
    text via Slack's `attachments` field — used for milestone events
    (done, panic) so they pop visually in a high-volume feed.

    See module docstring for the three branches and why we crash.
    """
    prefix = f"[{cfg.project_name}]"
    if owner:
        prefix += f" [{_mention(cfg, owner)}]"
    full_message = f"{prefix} {message}"
    if watchers:
        cc = [f"<@{cfg.slack_users[w]}>" for w in watchers if w in cfg.slack_users]
        if cc:
            full_message += f" (cc {' '.join(cc)})"

    if not cfg.slack_enabled:
        sys.stderr.write(f"[slack] disabled (post suppressed): {full_message}\n")
        return

    if not cfg.slack_webhook:
        sys.stderr.write(
            "[slack] $SLACK_WEBHOOK_URL is not set. "
            "Export it, or opt out with [slack].enabled = false in relay.local.toml.\n"
        )
        raise typer.Exit(1)

    payload: dict[str, object] = {"text": full_message}
    if image_url:
        payload["attachments"] = [{"image_url": image_url, "fallback": full_message}]

    try:
        requests.post(
            cfg.slack_webhook,
            json=payload,
            timeout=5,
        )
    except requests.RequestException as exc:
        sys.stderr.write(f"[slack] post failed: {exc}. Message was: {full_message}\n")
        if task_path is not None:
            append_log(task_path, "slack", f"post failed: {type(exc).__name__}: {exc}")
        raise typer.Exit(1)


__all__ = ["post"]
