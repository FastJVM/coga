"""Notification dispatch.

Coga notifications are the sync point between asynchronous agents and the
humans approving, unblocking, or watching their work. Slack is the first
backend behind this channel-agnostic surface.

`post` is the **live** path for urgent events (`coga block` and the manual
`coga slack` FYI). It selects the configured notification channel(s) and
dispatches through their backend implementation. Slack preserves the previous
crash-loud/no-retry semantics.

`notify` is the **outcome** path, not a generic lifecycle broadcaster. Only
ticket outcomes (`done` / `canceled`) and recurring scan errors go through it,
and they post live as they happen. Routine lifecycle churn (draft, active,
bump, paused, retire, recurring create) is intentionally silent: the
repo-global `coga/log.md` remains the audit trail, while notifications carry
outcomes and urgent exceptions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from coga.config import Config
from coga.notification.slack import NotificationDeliveryError, SlackChannel


def _channels(cfg: Config) -> list[SlackChannel]:
    channels: list[SlackChannel] = []
    for name in cfg.notification_channels:
        if name == SlackChannel.name:
            channels.append(SlackChannel(cfg))
    return channels


def preflight_post(cfg: Config, *, important: bool = False) -> None:
    """Fail before a state mutation when a selected live channel is unusable."""
    for channel in _channels(cfg):
        if channel.cfg.slack_enabled:
            channel.require_webhook(important=important)


def post(
    cfg: Config,
    message: str,
    *,
    task_path: Path | None = None,
    owner: str | None = None,
    watchers: list[str] | None = None,
    image_url: str | None = None,
    important: bool = False,
    fatal: bool = True,
    record_failure: bool = True,
) -> None:
    """Post a live notification through every configured channel.

    `important` routes the message to the channel's alert destination — for
    Slack, the coga-important webhook — instead of the default one. Reserve it
    for posts that need a human to go do something.

    `fatal` (the default) keeps the crash-loud contract: a message that could
    not be delivered exits 1. Pass `fatal=False` for a broadcast that
    *announces a state change already written to disk* — a bump, mark, or block
    transition. Three reasons, the same ones git sync already answers to
    (`coga.git.sync_paths`): the markdown on disk is the source of truth, so
    the transition happened either way; the miss is already loud on stderr and
    in `log.md`; and crashing aborts the command *after* the write but before
    its remaining work — for the session-ending commands that means skipping
    `emit_done_marker`, which leaves a supervised REPL wedged until its idle
    backstop kills it (a real 15-minute stall: a network-restricted agent
    sandbox turned a successful `coga bump` into a `timed_out` task). A
    delivery miss must not decide whether a session ends.

    Configuration failures (no webhook resolved for the requested route) crash
    on the fatal path — a rerun reproduces them identically, so the crash is
    the fix. Under `fatal=False` they are reported and returned like a delivery
    miss, for the same reason: the announced change is already on disk, and a
    misconfigured alert sink must not abort work that has nothing to do with
    it. The recurring sweep is the case that forced this — an unresolved
    `important_webhook` took down the whole scan phase, before any period task
    ran, over a *skipped-template summary* already printed to stderr and in the
    scan table. `preflight_post` remains the fail-fast configuration gate, and
    it runs before the mutation rather than after it.

    A strict feature publisher may set ``record_failure=False`` after it has
    atomically published lifecycle state. Delivery still fails loud on stderr,
    but the backend must not append a new, unleased audit line that would dirty
    or later sweep the protected feature checkout.
    """
    channels = _channels(cfg)
    if not channels:
        sys.stderr.write(f"[notification] no channels configured: {message}\n")
        return
    for channel in channels:
        try:
            channel.send(
                message,
                task_path=task_path,
                owner=owner,
                watchers=watchers,
                image_url=image_url,
                important=important,
                record_failure=record_failure,
            )
        except NotificationDeliveryError:
            # Already reported to stderr and, unless the strict-publisher
            # exception suppressed it, `log.md`; a fatal caller keeps exiting
            # 1. Remaining channels are still attempted when non-fatal.
            if fatal:
                raise typer.Exit(1) from None
        except typer.Exit:
            # The channel's own configuration refusal (no webhook resolved for
            # the requested route). It has already written the remedy to
            # stderr, so a non-fatal caller — one announcing a change already
            # written to disk — reports it and finishes its remaining work
            # rather than letting a misconfigured sink abort unrelated work.
            # `preflight_post` is the fail-fast configuration gate that still
            # crashes, before any mutation.
            if fatal:
                raise


# --- outcome path -------------------------------------------------------------

OUTCOME_EVENT_KINDS = {"done", "canceled", "recurring-error"}


def notify(
    cfg: Config,
    slack_text: str,
    *,
    kind: str,
    owner: str | None = None,
    watchers: list[str] | None = None,
    task_path: Path | None = None,
    image_url: str | None = None,
    important: bool = False,
    fatal: bool = True,
    record_failure: bool = True,
) -> None:
    """Post an outcome/error event live.

    Only `done`, `canceled`, and `recurring-error` belong here. Other lifecycle
    transitions are intentionally silent and should not call this helper; the
    `kind` gate is what keeps `notify` an outcome channel rather than a general
    broadcaster.

    Everything else forwards to `post` unchanged: `important` picks the alert
    destination, `image_url` and `owner`/`watchers` drive the `[project]
    [owner]` formatting, and `fatal` keeps its `post` meaning. The outcome
    callers (`mark done` / `mark canceled`, and the recurring scan-error
    summary) announce something already written to disk or already reported,
    so they pass `fatal=False` and neither a delivery miss nor an unresolved
    webhook aborts their remaining work. ``record_failure=False`` is the
    strict-publication form: a delivery miss remains visible on stderr without
    appending an unleased log line after the protected transition.
    """
    if kind not in OUTCOME_EVENT_KINDS:
        allowed = ", ".join(sorted(OUTCOME_EVENT_KINDS))
        raise ValueError(
            f"notification.notify only accepts outcome kinds: {allowed}"
        )
    post(
        cfg,
        slack_text,
        task_path=task_path,
        owner=owner,
        watchers=watchers,
        image_url=image_url,
        important=important,
        fatal=fatal,
        record_failure=record_failure,
    )


__all__ = [
    "post",
    "notify",
    "OUTCOME_EVENT_KINDS",
    "NotificationDeliveryError",
    "SlackChannel",
]
