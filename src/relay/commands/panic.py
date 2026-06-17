"""`relay panic` — agent is stuck, write blocker + notify owner."""

from __future__ import annotations

import sys

import typer

from relay import git
from relay.blackboard import append_blocker
from relay.config import ConfigError, load_config
from relay.logfile import append_log
from relay.repl_supervisor import emit_done_marker
from relay.notification import post
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def panic(
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
    reason: str = typer.Option(..., "--reason", help="Why the agent is stuck."),
) -> None:
    """Agent is stuck. Write blocker, notify owner."""
    if not reason.strip():
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
    actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"

    append_blocker(ref.path, actor, reason)
    append_log(ref.path, actor, f"panic: {reason}")

    owner = ticket.owner or cfg.current_user
    panicker = ticket.assignee or cfg.current_user
    post(
        cfg,
        f"🚨 {panicker} needs help on *{ref.id_slug}* "
        f"\"{ticket.title}\": {reason}",
        task_path=ref.path,
        owner=owner,
        watchers=ticket.watchers,
        image_url=cfg.gif_for("panic"),
    )
    typer.echo(f"{ref.id_slug}: panicked (owner {owner} notified)")
    # Sync the blocker (blackboard + log) to the control branch, the git
    # analogue of the notification post above. Scoped to the task dir by
    # `sync_task_state` — never `git add -A` — so the feature worktree's
    # uncommitted *code* (panic often fires from inside one) is left alone.
    # Run it before `emit_done_marker` so the commit/push completes while we
    # still own the process, not after a supervising `relay launch` has begun
    # reaping the REPL on the teardown signal.
    git.sync_task_state(cfg, ref.path, message=f"Ticket: {ref.id_slug} — panic")
    # Panic *is* the session-end transition: tell a supervising
    # `relay launch` to tear down the agent's REPL. The non-zero exit
    # below is the distress signal, not a failure of panic itself. The
    # resolved task path scopes the signal to this ticket (see
    # `emit_done_marker`).
    emit_done_marker(session_id=str(ref.path.resolve()))
    # Panic is the agent's distress signal — exit non-zero so a parent shell
    # or supervising agent can distinguish a panicked child from a clean one.
    sys.exit(1)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
