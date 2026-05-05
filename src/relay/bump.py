"""Step transitions — the shared core of `relay bump` and `relay automerge`.

Both commands need to:
  - mutate ticket frontmatter (advance step OR mark done)
  - append a line to log.md
  - release the lock when done
  - echo the local outcome to stdout
  - post to Slack

The CLI command (`relay bump`) and the auto-merge scanner reuse the
finalizers below so the on-disk shape stays identical regardless of who
triggered the transition. Only the log line, the Slack text, and the
actor differ between the two callers — those come in as arguments.
"""

from __future__ import annotations

import typer

from relay.config import Config
from relay.lock import TaskLock
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
    """Flip a ticket to `done`: write frontmatter, log, release lock, post.

    `echo` is the stdout line printed before the Slack post (so the local
    outcome is visible even if Slack crashes). Pass `None` to suppress —
    used by the quiet auto-bump path inside `relay status`.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(ref.path / "ticket.md")
    append_log(ref.path, actor, log_message)
    TaskLock(ref.path).release()
    if echo is not None:
        typer.echo(echo)
    post(cfg, slack_text, task_path=ref.path, owner=owner, image_url=image_url)


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
    "mark_done",
    "advance_step",
    "resolve_step_assignee",
    "AssigneeResolutionError",
]
