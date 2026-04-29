"""`relay feed` — post an FYI to the team Slack channel."""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.logfile import append_log
from relay.slack import post
from relay.tasks import (
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


def feed(
    task: str = typer.Option(..., "--task", help="Task ID or id-slug."),
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
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)
    actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"

    post(
        cfg,
        f"{ticket.assignee or cfg.current_user}: {message} "
        f"({ref.id_slug})",
        task_path=ref.path,
    )
    append_log(ref.path, actor, f"feed: {message}")
    typer.echo("posted")


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
