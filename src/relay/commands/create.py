"""Raw draft-ticket scaffolding for `relay draft` / legacy `relay create`.

Posts ✨ to Slack and leaves the new ticket as `draft`. Does not launch
an agent. For guided authoring use `relay ticket`; to start work, mark the
ticket active and then launch it.

`--workflow` is optional: a workflow-less draft is a valid authoring
intermediate, it just can't be activated. `relay mark active` refuses a
ticket with no workflow (workflow-less tickets can never be `relay bump`ed),
so add a `workflow:` before activating, or pass `--workflow` up front.
"""

from __future__ import annotations

import sys

import typer

from relay.config import ConfigError, load_config
from relay.scaffold import scaffold_task
from relay.slack import post


def draft(
    title: str = typer.Argument(..., help="Short human title for the new ticket."),
    mode: str = typer.Option(
        "interactive",
        "--mode",
        help="Ticket mode: interactive, auto, or script.",
    ),
    workflow: str | None = typer.Option(
        None,
        "--workflow",
        help=(
            "Workflow name (path under relay-os/workflows/) to attach. "
            "Optional, but a workflow-less draft can't be activated until "
            "one is added."
        ),
    ),
) -> None:
    """Scaffold a new draft ticket and post ✨ to Slack."""
    scaffold_draft(title=title, mode=mode, workflow=workflow)


def create(
    title: str = typer.Argument(..., help="Short human title for the new ticket."),
    mode: str = typer.Option(
        "interactive",
        "--mode",
        help="Ticket mode: interactive, auto, or script.",
    ),
    workflow: str | None = typer.Option(
        None,
        "--workflow",
        help=(
            "Workflow name (path under relay-os/workflows/) to attach. "
            "Optional, but a workflow-less draft can't be activated until "
            "one is added."
        ),
    ),
) -> None:
    """Compatibility spelling for `relay draft`."""
    scaffold_draft(title=title, mode=mode, workflow=workflow)


def scaffold_draft(
    *,
    title: str,
    mode: str,
    workflow: str | None = None,
) -> dict[str, object]:
    """Scaffold a raw draft ticket and post the create notification.

    `workflow` is optional. A workflow-less draft is a valid authoring
    intermediate — `relay mark active` is the gate that refuses to activate
    a ticket with no workflow, since a workflow-less ticket can never be
    `relay bump`ed.
    """
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
            workflow_name=workflow,
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
    return result


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
