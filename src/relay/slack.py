"""Slack webhook poster.

When `slack.webhook` is set in relay.toml, every call POSTs JSON `{text: ...}`.
Otherwise messages are written to stderr prefixed with `[slack]` so dev/test
runs still surface the traffic.
"""

from __future__ import annotations

import sys

import requests

from relay.config import Config


def post(cfg: Config, message: str) -> None:
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


__all__ = ["post"]
