"""`coga status` — one line per task in the repo.

Thin Typer head: the directory operand + flag surface and error→exit
translation live here; the render itself is `coga.views.render_status`.
"""

from __future__ import annotations

import sys

import typer

from coga.config import ConfigError, load_config
from coga.tasks import UnknownDirectoryError
from coga.views import ORDER_BY_CHOICES, ViewError, render_status


def status(
    directory: str | None = typer.Argument(
        None,
        metavar="[DIR]",
        help=(
            "Show only tasks under `tasks/<DIR>/` (a directory path, nested "
            "ones included, e.g. `marketing` or `marketing/social`). Omit to "
            "show every task; add --no-recurse to show only the top level."
        ),
    ),
    no_recurse: bool = typer.Option(
        False,
        "--no-recurse",
        help=(
            "List only tasks sitting directly in the directory, none from "
            "sub-directories. With no DIR, shows the tasks directly under "
            "tasks/ (the top-level slice)."
        ),
    ),
    order_by: str = typer.Option(
        "updated",
        "--order-by",
        "-o",
        help=f"Sort column. One of: {', '.join(ORDER_BY_CHOICES)}.",
    ),
    reverse: bool = typer.Option(
        False, "--reverse", "-r", help="Reverse sort order."
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Include terminal `done` and `canceled` tasks (hidden by default).",
    ),
    dirs: bool = typer.Option(
        False,
        "--dirs",
        "-d",
        help=(
            "List the plain (non-task) directories under tasks/ instead of the "
            "tasks themselves, one path per line. Honors DIR (sub-dirs of that "
            "directory) and --no-recurse (only the immediate level)."
        ),
    ),
    blocked: bool = typer.Option(
        False,
        "--blocked",
        help="Show only blocked tickets, expanding every open blocker ask.",
    ),
) -> None:
    """Show tasks in the repo."""
    try:
        cfg = load_config(require_user=False)
    except ConfigError as exc:
        _bail(str(exc))

    try:
        render_status(
            cfg,
            directory=directory,
            no_recurse=no_recurse,
            order_by=order_by,
            reverse=reverse,
            show_all=show_all,
            dirs=dirs,
            blocked=blocked,
        )
    except (ViewError, UnknownDirectoryError) as exc:
        _bail(str(exc))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
