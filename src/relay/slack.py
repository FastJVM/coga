"""Slack webhook poster — two-tier (@mention vs FYI) routing.

Behavior:
- When `slack.webhook` is set in relay.toml, every call POSTs JSON `{text: ...}`.
- When no webhook is configured, messages are written to stderr prefixed with
  `[slack]` so dev/test runs still surface the traffic.
- `post_mention(user, message)` rewrites to `<@SLACKID> — message` using the
  `slack` field on the matching assignee. If the assignee isn't mapped, it
  falls back to `@username — message` (human-readable but not a real tag).
"""

from __future__ import annotations

import sys

import requests

from relay.config import Config


def post_feed(cfg: Config, message: str) -> None:
    """FYI message, no @mention."""
    _post(cfg, message)


def post_mention(cfg: Config, user: str, message: str) -> None:
    """Message that @mentions a specific user."""
    tag = _mention_tag(cfg, user)
    _post(cfg, f"{tag} — {message}")


# --- internals ----------------------------------------------------------------


def _mention_tag(cfg: Config, user: str) -> str:
    """Resolve a user name to a Slack mention string."""
    assignee = cfg.assignees.get(user)
    if assignee and assignee.slack:
        return f"<@{assignee.slack}>"
    return f"@{user}"


def _post(cfg: Config, text: str) -> None:
    if not cfg.slack_webhook:
        sys.stderr.write(f"[slack] {text}\n")
        return
    try:
        requests.post(
            cfg.slack_webhook,
            json={"text": text},
            timeout=5,
        )
    except requests.RequestException as exc:
        sys.stderr.write(f"[slack] post failed: {exc}. Message was: {text}\n")


__all__ = ["post_feed", "post_mention"]
