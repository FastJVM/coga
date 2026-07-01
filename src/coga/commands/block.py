"""`coga block` — normal workflow stop for concrete human input."""

from __future__ import annotations

import sys

import typer

from coga.blackboard import append_blocker
from coga.config import ConfigError, load_config
from coga.mark import mark_blocked
from coga.repl_supervisor import emit_done_marker
from coga.tasks import TaskNotFoundError, read_ticket, resolve_task
from coga.validate import TaskValidationError


def block(
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
    reason: str = typer.Option(
        ...,
        "--reason",
        help="Specific answer needed before the task can continue.",
    ),
) -> None:
    """Record an unresolved blocker and set the ticket to `blocked`."""
    reason = reason.strip()
    if not reason:
        _bail("--reason cannot be empty")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)
    if ticket.status not in {"active", "in_progress", "blocked"}:
        _bail(
            f"Task {ref.id_slug} is {ticket.status!r}; block requires "
            "'active', 'in_progress', or 'blocked'."
        )

    actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"
    append_blocker(ref.ticket_path, actor, reason)

    owner = ticket.owner or cfg.current_user
    blocker = ticket.assignee or cfg.current_user
    ticket = read_ticket(ref)
    try:
        mark_blocked(
            cfg,
            ref,
            ticket,
            actor=actor,
            log_message=f"blocked: {reason}",
            slack_text=(
                f"🛑 {blocker} blocked *{ref.id_slug}* "
                f"\"{ticket.title}\": {reason}"
            ),
            image_url=cfg.gif_for("block") or cfg.gif_for("panic"),
            echo=f"{ref.id_slug}: blocked (owner {owner} needs to answer)",
        )
    except TaskValidationError as exc:
        _bail(str(exc))

    emit_done_marker(session_id=str(ref.path.resolve()))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
