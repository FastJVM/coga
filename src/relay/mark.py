"""Status transitions — the shared core of `relay mark` and `relay automerge`.

These finalizers mutate ticket frontmatter, append a `log.md` line, echo the
local outcome, and post to Slack. The CLI commands and the auto-merge scanner
all reuse the same helpers so the on-disk shape stays identical regardless
of who triggered the transition.

`advance_step` lives in `relay.bump` — that's the workflow plane.
"""

from __future__ import annotations

import typer

from relay.config import Config
from relay.logfile import append_log
from relay.slack import post
from relay.tasks import TaskRef
from relay.ticket import Ticket
from relay.validate import assert_task_valid


def mark_done(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    image_url: str | None = None,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `done`: write frontmatter, log, post.

    `echo` is the stdout line printed before the Slack post (so the local
    outcome is visible even if Slack crashes). Pass `None` to suppress —
    used by the quiet auto-bump path inside `relay status`.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action="mark done")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path, owner=owner, image_url=image_url)


class RequiredExtensionMissing(RuntimeError):
    """Raised when `mark active` is called on a ticket with required-but-empty
    extension fields. The caller renders a per-field error message for the
    user.
    """

    def __init__(self, fields: list[str]):
        self.fields = fields
        super().__init__(
            f"ticket missing values for required extension fields: {fields}"
        )


def _missing_required_extensions(cfg: Config, ticket: Ticket) -> list[str]:
    """Return names of `required = true` extension fields that are absent or
    empty on this ticket."""
    missing: list[str] = []
    for name, spec in cfg.ticket_fields.items():
        if not spec.required:
            continue
        value = ticket.frontmatter.get(name, "")
        if not isinstance(value, str) or not value.strip():
            missing.append(name)
    return missing


def mark_active(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `active`: write frontmatter, log, post.

    Refuses to activate if any `required = true` extension field is empty.
    """
    missing = _missing_required_extensions(cfg, ticket)
    if missing:
        raise RequiredExtensionMissing(missing)

    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "active"
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action="mark active")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path, owner=owner)


def mark_in_progress(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `in_progress`: write frontmatter, log, optionally post."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action="mark in_progress")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        post(cfg, slack_text, task_path=ref.path, owner=owner)


def mark_paused(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `paused`: write frontmatter, log, post."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "paused"
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action="mark paused")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path, owner=owner)


__all__ = [
    "mark_active",
    "mark_in_progress",
    "mark_paused",
    "mark_done",
    "RequiredExtensionMissing",
]
