"""Slack notification channel backend."""

from __future__ import annotations

import sys
from pathlib import Path

import requests
import typer

from relay.config import Config
from relay.logfile import append_log, ref_tag_for_path
from relay.slack_response import classify_slack_response


def mention(cfg: Config, name: str) -> str:
    """Render `name` as a Slack ping when its member ID is mapped."""
    user_id = cfg.slack_users.get(name)
    return f"<@{user_id}>" if user_id else name


class SlackChannel:
    """Slack webhook backend for Relay notifications."""

    name = "slack"

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def render_text(
        self,
        message: str,
        *,
        owner: str | None = None,
        watchers: list[str] | None = None,
    ) -> str:
        """Add Relay's project/owner prefix and mapped watcher cc trailer."""
        prefix = f"[{self.cfg.project_name}]"
        if owner:
            prefix += f" [{mention(self.cfg, owner)}]"
        full_message = f"{prefix} {message}"
        if watchers:
            cc = [
                f"<@{self.cfg.slack_users[w]}>"
                for w in watchers
                if w in self.cfg.slack_users
            ]
            if cc:
                full_message += f" (cc {' '.join(cc)})"
        return full_message

    def send(
        self,
        message: str,
        *,
        task_path: Path | None = None,
        owner: str | None = None,
        watchers: list[str] | None = None,
        image_url: str | None = None,
    ) -> None:
        """Post a message through Slack, or crash trying."""
        full_message = self.render_text(message, owner=owner, watchers=watchers)

        if not self.cfg.slack_enabled:
            sys.stderr.write(f"[slack] disabled (post suppressed): {full_message}\n")
            return

        if not self.cfg.slack_webhook:
            sys.stderr.write(
                "[notification.slack] Slack is selected in "
                "[notification].channels but no webhook is configured. Set "
                "[notification.slack].webhook in relay.toml "
                '(e.g. webhook = "env:SLACK_WEBHOOK_URL", then export '
                "SLACK_WEBHOOK_URL), remove slack from [notification].channels "
                "to run without it, or opt out with "
                "[notification.slack].enabled = false in relay.local.toml.\n"
            )
            raise typer.Exit(1)

        payload: dict[str, object] = {"text": full_message}
        if image_url:
            payload["attachments"] = [
                {"image_url": image_url, "fallback": full_message}
            ]

        def fail(message: str, log_detail: str) -> None:
            sys.stderr.write(
                f"[slack] post failed: {message}. Message was: {full_message}\n"
            )
            if task_path is not None:
                append_log(self.cfg, ref_tag_for_path(self.cfg, task_path), "slack", f"post failed: {log_detail}")
            raise typer.Exit(1)

        try:
            resp = requests.post(
                self.cfg.slack_webhook,
                json=payload,
                timeout=5,
            )
        except requests.RequestException as exc:
            fail(
                f"network error: {exc}",
                f"{type(exc).__name__}: {exc}",
            )

        status, detail = classify_slack_response(resp.status_code, resp.text)
        if status == "revoked":
            fail(
                f"revoked/invalid webhook: {detail}",
                f"revoked/invalid webhook: {detail}",
            )
        if not 200 <= resp.status_code < 300:
            if status == "unreachable":
                fail(
                    f"transient Slack HTTP failure: {detail}",
                    f"transient HTTP failure: {detail}",
                )
            fail(
                f"non-OK Slack response: {detail}",
                f"non-OK response: {detail}",
            )
