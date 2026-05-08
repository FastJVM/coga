"""`relay delete` — remove a task directory from the working tree."""

from __future__ import annotations

import sys
import shutil

import typer

from relay.config import ConfigError, load_config
from relay.lock import TaskLock
from relay.tasks import (
    TaskNotFoundError,
    list_tasks,
    resolve_task,
)


def delete(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Delete even if task.lock is held.",
    ),
    exact: bool = typer.Option(
        False,
        "--exact",
        help="Require an exact task slug. Use this for scripted deletion.",
    ),
) -> None:
    """Remove a task directory. Recovery is via `git restore`."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        if exact:
            exact_refs = [ref for ref in list_tasks(cfg) if ref.slug == task]
            if not exact_refs:
                raise TaskNotFoundError(f"No exact task slug matches {task!r}")
            ref = exact_refs[0]
        else:
            ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    lock = TaskLock(ref.path).read()
    if lock is not None and not force:
        _bail(
            f"{ref.id_slug}: task.lock held by {lock.holder!r} "
            f"since {lock.acquired.isoformat()} - pass --force to delete anyway."
        )

    shutil.rmtree(ref.path)
    typer.echo(f"{ref.id_slug}: deleted")


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
