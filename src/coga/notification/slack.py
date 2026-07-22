"""Slack notification channel backend."""

from __future__ import annotations

import sys
from pathlib import Path

import requests
import typer

from coga.config import Config
from coga.logfile import append_log, ref_tag_for_path
from coga.slack_response import classify_slack_response, format_slack_request_error


def mention(cfg: Config, name: str) -> str:
    """Render `name` as a Slack ping when its member ID is mapped."""
    user_id = cfg.slack_users.get(name)
    return f"<@{user_id}>" if user_id else name


class SlackChannel:
    """Slack webhook backend for Coga notifications."""

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
        """Add Coga's project/owner prefix and mapped watcher cc trailer."""
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

    def webhook_for(self, *, important: bool) -> str | None:
        """The webhook an important / routine post should go to.

        An important post must reach the coga-important channel or fail — it is
        never silently rerouted to the default webhook. A repo that asks for
        `--important` without a resolved `important_webhook` is misconfigured,
        and delivering a human-action alert to the wrong channel while reporting
        success is worse than crashing: the crash is what gets the config fixed.
        Downstream repos each carry their own `coga.toml`, so the unconfigured
        case is live, not theoretical.
        """
        if not important:
            return self.cfg.slack_webhook
        if self.cfg.slack_important_webhook:
            return self.cfg.slack_important_webhook
        sys.stderr.write(
            "[notification.slack] --important was requested but no "
            "important_webhook is resolved, so this alert has nowhere to go. "
            'Set [notification.slack].important_webhook = "env:VAR" in this '
            "repo's coga.toml and export VAR (the key and the exported variable "
            "are two separate steps; either one missing lands you here).\n"
        )
        raise typer.Exit(1)

    def send(
        self,
        message: str,
        *,
        task_path: Path | None = None,
        owner: str | None = None,
        watchers: list[str] | None = None,
        image_url: str | None = None,
        important: bool = False,
    ) -> None:
        """Post a message through Slack, or crash trying."""
        full_message = self.render_text(message, owner=owner, watchers=watchers)

        if not self.cfg.slack_enabled:
            sys.stderr.write(f"[slack] disabled (post suppressed): {full_message}\n")
            return

        webhook = self.webhook_for(important=important)
        if not webhook:
            sys.stderr.write(
                "[notification.slack] Slack is selected in "
                "[notification].channels but no webhook is configured. Set "
                "[notification.slack].webhook in coga.toml "
                '(e.g. webhook = "env:SLACK_WEBHOOK_URL", then export '
                "SLACK_WEBHOOK_URL), remove slack from [notification].channels "
                "to run without it, or opt out with "
                "[notification.slack].enabled = false in coga.local.toml.\n"
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
                webhook,
                json=payload,
                timeout=5,
            )
        except requests.RequestException as exc:
            detail = format_slack_request_error(exc)
            fail(
                f"network error: {detail}",
                detail,
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
