"""`coga block` — normal workflow stop for concrete human input."""

from __future__ import annotations

import sys

import typer

from coga import git
from coga import pr_assist
from coga.blackboard import append_blocker
from coga.commands.common import current_operator
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

    try:
        assist = pr_assist.assist_session_from_env(cfg, ref)
    except git.GitError as exc:
        _bail(f"Could not rebuild {ref.id_slug}'s recorded assist session: {exc}")
    effective_agent = (
        assist.agent
        if assist is not None
        else current_operator(cfg, ref, ticket)
    )
    actor = (
        f"agent:{effective_agent}"
        if effective_agent
        else f"human:{cfg.current_user}"
    )
    owner = ticket.owner or cfg.current_user
    blocker = effective_agent or cfg.current_user

    try:
        with git.state_lock(cfg):
            append_blocker(ref.ticket_path, actor, reason)
        ticket = read_ticket(ref)
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

    # `id_slug` (not the resolved path) scopes the signal so it matches the
    # supervisor regardless of which checkout the command runs in. See
    # `bump.py` for the path-drift rationale.
    emit_done_marker(session_id=ref.id_slug)


def _bail(msg: str, *, exit_code: int = 2) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(exit_code)
