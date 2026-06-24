"""`relay show` — print a task's ticket (with its blackboard) and log history."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from relay.config import ConfigError, load_config
from relay.logfile import task_log_lines
from relay.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    resolve_target,
)


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
        ref = resolve_target(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    console = Console()

    # The single-file ticket.md carries frontmatter + body + blackboard.
    console.print(Rule(f"{ref.id_slug}/ticket.md"))
    console.print()
    ticket_path = ref.ticket_path
    if not ticket_path.is_file():
        console.print("[dim](no ticket.md)[/dim]")
    else:
        text = ticket_path.read_text()
        console.print(Markdown(text) if text.strip() else "[dim](empty)[/dim]")

    # Bootstrap tickets are stateless: no log history to reconstruct.
    if isinstance(ref, BootstrapRef):
        return

    console.print()
    console.print(Rule(f"{ref.id_slug} — log (from relay-os/log.md)"))
    console.print()
    lines = task_log_lines(cfg, ref.id_slug)
    if not lines:
        console.print("[dim](no log entries)[/dim]")
    else:
        for line in lines:
            console.print(line)


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
