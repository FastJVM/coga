"""`relay show` — print a task's ticket, blackboard, and log to the terminal."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from relay.config import ConfigError, load_config
from relay.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    resolve_target,
)


def show(
    task: str = typer.Argument(..., help="Task ID, id-slug, or `bootstrap/<name>`."),
) -> None:
    """Print a task's contents — ticket, blackboard, log — rendered as markdown."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_target(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    console = Console()

    # Bootstrap tickets are stateless: only ticket.md is meaningful.
    files = ["ticket.md"] if isinstance(ref, BootstrapRef) else ["ticket.md", "blackboard.md", "log.md"]

    for i, name in enumerate(files):
        path = ref.path / name
        if i > 0:
            console.print()
        console.print(Rule(f"{ref.id_slug}/{name}"))
        console.print()
        if not path.is_file():
            console.print(f"[dim](no {name})[/dim]")
            continue
        text = path.read_text()
        if not text.strip():
            console.print(f"[dim](empty)[/dim]")
            continue
        console.print(Markdown(text))


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
