"""`relay panic` — agent is stuck, write blocker + @mention owner + release lock."""

from __future__ import annotations

import sys

import typer

from relay.blackboard import append_blocker
from relay.config import ConfigError, load_config
from relay.lock import TaskLock
from relay.logfile import append_log
from relay.slack import post_mention
from relay.tasks import (
    AmbiguousTaskError,
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def panic(
    task: str = typer.Option(..., "--task", help="Task ID or project/id."),
    reason: str = typer.Option(..., "--reason", help="Why the agent is stuck."),
) -> None:
    """Agent is stuck. Write blocker, @mention owner, release lock."""
    if not reason.strip():
        _bail("--reason cannot be empty")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except (TaskNotFoundError, AmbiguousTaskError) as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)
    actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"

    append_blocker(ref.path, actor, reason)
    append_log(ref.path, actor, f"panic: {reason}")

    # Release the lock so a human can relaunch.
    TaskLock(ref.path).release()

    owner = ticket.owner or cfg.current_user
    post_mention(
        cfg,
        owner,
        f"{ref.project} {ref.id_slug} \"{ticket.title}\" — agent stuck: \"{reason}\"",
    )
    typer.echo(f"{ref.project}/{ref.id_slug}: panicked (owner @{owner} notified)")


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
