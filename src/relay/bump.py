"""Step advancement — the workflow plane.

`relay bump` advances exactly one workflow step. Status transitions
(active/paused/done) live in `relay.mark`.
"""

from __future__ import annotations

import typer

from relay.config import Config
from relay.logfile import append_log
from relay.slack import post
from relay.tasks import TaskRef
from relay.ticket import Ticket
from relay.workflow import VALID_ASSIGNEE_ROLES


class AssigneeResolutionError(Exception):
    """Raised when a workflow step's role token can't resolve against the ticket."""


def resolve_step_assignee(ticket: Ticket, role: str) -> str:
    """Resolve a workflow step's role token to a concrete nickname.

    `role` must be one of `owner` | `human` | `agent`. Raises
    AssigneeResolutionError if the ticket has no value for that role.
    """
    if role not in VALID_ASSIGNEE_ROLES:
        raise AssigneeResolutionError(
            f"Unknown role token {role!r} (expected one of {sorted(VALID_ASSIGNEE_ROLES)})"
        )
    value = ticket.frontmatter.get(role)
    if not value:
        raise AssigneeResolutionError(
            f"Workflow step declares assignee={role!r} but ticket has no `{role}:` field. "
            f"Add `{role}: <nickname>` to ticket frontmatter."
        )
    return str(value)


def advance_step(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    next_step: int,
    new_step_name: str,
    actor: str,
    log_message: str,
    slack_text: str,
    new_assignee: str | None = None,
    echo: str | None = None,
) -> None:
    """Advance a ticket to the next workflow step.

    If `new_assignee` is given, also rewrites the ticket's `assignee:` to that
    nickname. Caller is responsible for resolving role tokens against the
    ticket beforehand (see `resolve_step_assignee`).
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["step"] = f"{next_step} ({new_step_name})"
    if new_assignee is not None:
        ticket.frontmatter["assignee"] = new_assignee
    ticket.write(ref.path / "ticket.md")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path, owner=owner)


__all__ = [
    "advance_step",
    "resolve_step_assignee",
    "AssigneeResolutionError",
]
