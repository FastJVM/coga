"""`relay create "<title>"` — scaffold a new draft ticket.

Posts ✨ to Slack and leaves the new ticket as `draft`. Does not launch
an agent. To start work, edit the draft (workflow, contexts, description),
then `relay mark active <slug>` and `relay launch <slug>`.
"""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.scaffold import scaffold_task
from relay.slack import post


def create(
    title: str = typer.Argument(..., help="Short human title for the new ticket."),
    mode: str = typer.Option(
        "interactive",
        "--mode",
        help="Ticket mode: interactive, auto, or script.",
    ),
) -> None:
    """Scaffold a new draft ticket and post ✨ to Slack."""
    if not title.strip():
        _bail("title cannot be empty")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        result = scaffold_task(
            cfg=cfg,
            title=title,
            workflow_name=None,
            contexts=[],
            mode=mode,
            owner=cfg.current_user,
            assignee=None,
            watchers=[],
            status="draft",
        )
    except ValueError as exc:
        _bail(str(exc))

    slug = result["slug"]
    typer.echo(f"{slug}: created (draft)")
    post(
        cfg,
        f"✨ {cfg.current_user} created *{slug}* "
        f"\"{title}\" in {cfg.project_name}",
        task_path=result["path"],
        owner=cfg.current_user,
    )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
