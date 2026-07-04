"""`coga show` — print a task's ticket (with its blackboard) and log history.

Thin Typer head: the `<task>` operand and error→exit translation live here; the
render itself is `coga.views.render_show` (also exposed as the `coga/show`
script skill).
"""

from __future__ import annotations

import sys

import typer

from coga.config import ConfigError, load_config
from coga.tasks import TaskNotFoundError
from coga.views import render_show


def show(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>`."),
) -> None:
    """Print a task's contents — its single-file ticket (frontmatter + body +
    blackboard) and, for a real task, its history reconstructed from the
    repo-global log."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        render_show(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
