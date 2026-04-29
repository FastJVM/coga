"""`relay panic` — agent is stuck, write blocker + notify owner + release lock."""

from __future__ import annotations

import sys

import typer

from relay.blackboard import append_blocker
from relay.config import ConfigError, load_config
from relay.lock import TaskLock
from relay.logfile import append_log
from relay.slack import post
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def panic(
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
    reason: str = typer.Option(..., "--reason", help="Why the agent is stuck."),
) -> None:
    """Agent is stuck. Write blocker, notify owner, release lock."""
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

    # Release the lock so a human can relaunch.
    TaskLock(ref.path).release()

    owner = ticket.owner or cfg.current_user
    post(
        cfg,
        f"{owner}: {ref.id_slug} \"{ticket.title}\" — agent stuck: \"{reason}\"",
    )
    typer.echo(f"{ref.id_slug}: panicked (owner {owner} notified)")
    # Panic is the agent's distress signal — exit non-zero so a parent shell
    # or supervising agent can distinguish a panicked child from a clean one.
    sys.exit(1)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
