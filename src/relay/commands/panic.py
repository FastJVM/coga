"""`relay panic` — agent is stuck, write blocker + notify owner."""

from __future__ import annotations

import sys

import typer

from relay.blackboard import append_blocker
from relay.config import ConfigError, load_config
from relay.logfile import append_log
from relay.repl_supervisor import emit_done_marker
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
        f"\"{ticket.title}\" — \"{reason}\"",
        task_path=ref.path,
        owner=owner,
        watchers=ticket.watchers,
        image_url=cfg.gif_for("panic"),
    )
    typer.echo(f"{ref.id_slug}: panicked (owner {owner} notified)")
    # Panic *is* the session-end transition: tell a supervising
    # `relay launch` to tear down the agent's REPL. The non-zero exit
    # below is the distress signal, not a failure of panic itself.
    emit_done_marker()
    # Panic is the agent's distress signal — exit non-zero so a parent shell
    # or supervising agent can distinguish a panicked child from a clean one.
    sys.exit(1)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
