"""`relay feed` — post an FYI to the team Slack channel."""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.logfile import append_log
from relay.slack import post_feed
from relay.tasks import (
    AmbiguousTaskError,
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def feed(
    task: str = typer.Option(..., "--task", help="Task ID or project/id."),
    message: str = typer.Option(..., "--message", help="Short FYI message."),
) -> None:
    """Post an FYI to the team Slack channel."""
    if not message.strip():
        _bail("--message cannot be empty")

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

    post_feed(
        cfg,
        f"{ticket.assignee or cfg.current_user}: {message} "
        f"({ref.project} {ref.id_slug})",
    )
    append_log(ref.path, actor, f"feed: {message}")
    typer.echo("posted")


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
