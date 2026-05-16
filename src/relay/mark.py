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
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path, owner=owner, image_url=image_url)


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
    """Flip a ticket to `active`: write frontmatter, log, post."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "active"
    ticket.write(ref.path / "ticket.md")
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
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path, owner=owner)


__all__ = ["mark_active", "mark_in_progress", "mark_paused", "mark_done"]
