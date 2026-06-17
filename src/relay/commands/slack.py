"""`relay slack` — post an FYI through the notification system.

The manual broadcast escape hatch: state-machine transitions
(`launch`, `bump`, `panic`, `recurring`) already broadcast on
their own; this command covers the cases that don't fit one of those —
e.g. a human announcing they hand-edited a ticket, or an agent calling
out a non-transition event mid-step. For FYIs that *do* coincide with
a step transition, prefer `bump --message`.
"""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.logfile import append_log
from relay.notification import post
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def slack(
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
    message: str = typer.Option(..., "--message", help="Short FYI message."),
) -> None:
    """Post an FYI through the configured notification channel(s)."""
    if not message.strip():
        _bail("--message cannot be empty")

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

    post(
        cfg,
        f"💬 {ticket.assignee or cfg.current_user} on *{ref.id_slug}* "
        f"\"{ticket.title}\": {message}",
        task_path=ref.path,
        owner=ticket.owner or cfg.current_user,
        watchers=ticket.watchers,
    )
    append_log(ref.path, actor, f"slack: {message}")
    typer.echo("posted")


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
