"""Raw draft-ticket creating for `coga create`.

Leaves the new ticket as `draft`. Does not post to Slack and does not launch
an agent. For guided authoring use `coga ticket`; to start work, mark the
ticket active and then launch it.

`--workflow` is optional: a workflow-less draft is a valid authoring
intermediate, it just can't be activated. `coga mark active` refuses a
ticket with no workflow (workflow-less tickets can never be `coga bump`ed),
so add a `workflow:` before activating, or pass `--workflow` up front.
"""

from __future__ import annotations

import sys

import typer

from coga import git
from coga.config import ConfigError, load_config
from coga.create import create_task


def create(
    title: str = typer.Argument(..., help="Short human title for the new ticket."),
    autonomy: str = typer.Option(
        "interactive",
        "--autonomy",
        help="Ticket autonomy: interactive or auto.",
    ),
    workflow: str | None = typer.Option(
        None,
        "--workflow",
        help=(
            "Workflow name (path under coga-os/workflows/) to attach. "
            "Optional, but a workflow-less draft can't be activated until "
            "one is added."
        ),
    ),
) -> None:
    """Create a new raw draft ticket."""
    create_draft(title=title, autonomy=autonomy, workflow=workflow)


def create_draft(
    *,
    title: str,
    autonomy: str,
    workflow: str | None = None,
) -> dict[str, object]:
    """Create a raw draft ticket.

    Does not post to Slack — it just writes the ticket and git-syncs it.

    `workflow` is optional. A workflow-less draft is a valid authoring
    intermediate — `coga mark active` is the gate that refuses to activate
    a ticket with no workflow, since a workflow-less ticket can never be
    `coga bump`ed.
    """
    if not title.strip():
        _bail("title cannot be empty")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        result = create_task(
            cfg=cfg,
            title=title,
            workflow_name=workflow,
            contexts=[],
            autonomy=autonomy,
            owner=cfg.current_user,
            assignee=None,
            watchers=[],
            status="draft",
        )
    except ValueError as exc:
        _bail(str(exc))

    slug = result["slug"]
    typer.echo(f"{slug}: created (draft)")
    git.sync_task_state(cfg, result["path"], message=f"Ticket: {slug} — created")
    return result


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
