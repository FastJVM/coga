"""`coga delete` — remove a task directory from the working tree.

Both the command and the registered recipe use coga.delete_task.
"""

from __future__ import annotations

import sys

import typer

from coga.config import ConfigError, load_config
from coga.delete_task import DeleteTaskError, run_delete_task
from coga.tasks import TaskNotFoundError, resolve_task


def delete(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
) -> None:
    """Remove a task directory. Recovery is via `git restore`."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    try:
        output = run_delete_task(cfg, ref)
    except DeleteTaskError as exc:
        _bail(str(exc))
    if output:
        typer.echo(output, nl=False)



def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
