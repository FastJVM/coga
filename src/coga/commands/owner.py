"""`coga owner <slug> <name>` — reassign a ticket's human of record.

`owner:` is the one ticket-to-person relationship the model carries: the
`owner` step role resolves to it, megalaunch and the dependency drain select
on it, and Slack mentions derive from it. It is not agent-editable, and a
hand edit skips validation, the audit line, and the guarded control sync —
which is how a ticket ends up with `owner:` naming someone who handed it off
months ago. This command is the one writer, shaped like a `coga.mark`
transition: prospective validation, barrier write, audit line, guarded sync.
No Slack post — like `mark paused`, a reassignment is routine local noise.
"""

from __future__ import annotations

import sys

import typer

from coga import git
from coga.config import ConfigError, load_config
from coga.lifecycle import TERMINAL_STATUSES
from coga.logfile import append_log
from coga.tasks import TaskNotFoundError, read_ticket, resolve_task
from coga.ticket import Ticket
from coga.validate import TaskValidationError, assert_task_valid


def owner(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    name: str = typer.Argument(..., help="Coga name of the new owner."),
) -> None:
    """Set `owner:` to NAME. Allowed from every status except `in_progress`
    and the terminal outcomes."""
    name = name.strip()
    if not name:
        _bail("owner name cannot be empty")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)
    previous = ticket.owner
    if ticket.status in TERMINAL_STATUSES:
        _bail(
            f"Task {ref.id_slug} is {ticket.status!r}; a finished record keeps "
            "the owner it finished under."
        )
    if ticket.status == "in_progress":
        # A live session's routing lease compares `owner` (see
        # `git.TicketRoutingState`); changing it under a running agent would
        # invalidate that lease mid-step. Pausing ends the session first.
        _bail(
            f"Task {ref.id_slug} is 'in_progress'; run `coga mark paused "
            f"{ref.id_slug}` first, then reassign it."
        )
    if previous == name:
        _bail(f"Task {ref.id_slug} is already owned by {name!r}.")

    # Validate the prospective ticket before writing, so a refused
    # reassignment leaves nothing on disk to reconcile (the idiom
    # `coga/architecture` prescribes for every lifecycle writer).
    prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    prospective.frontmatter["owner"] = name
    try:
        assert_task_valid(cfg, ref, action="owner", ticket_override=prospective)
    except TaskValidationError as exc:
        _bail(str(exc))

    ticket.frontmatter = prospective.frontmatter
    git.write_ticket_under_barrier(cfg, ticket, ref.ticket_path)
    append_log(
        cfg,
        ref.id_slug,
        f"human:{cfg.current_user}",
        f"owner {previous!r} → {name!r}",
    )
    typer.echo(f"{ref.id_slug}: owner {previous} → {name}")
    git.sync_task_state(
        cfg,
        ref.path,
        message=f"Ticket: {ref.id_slug} — owner {name}",
        guard=git.ticket_state_guard(cfg, ref.ticket_path),
    )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
