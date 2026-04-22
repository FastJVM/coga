"""`relay status` — one line per task across projects."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from relay.config import ConfigError, load_config
from relay.tasks import list_tasks, read_ticket
from relay.ticket import TicketError


def status(
    project: str = typer.Option(None, "--project", help="Limit to one project."),
    all: bool = typer.Option(False, "--all", help="Include done/canceled/failed tasks."),
) -> None:
    """Show tasks across projects."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    refs = list_tasks(cfg, project)
    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    for col in ("project", "id", "title", "status", "assignee", "step", "mode"):
        table.add_column(col)

    hidden = {"done", "canceled", "failed"}
    rows = 0
    for ref in refs:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if not all and ticket.status in hidden:
            continue
        step = ticket.step or "-"
        assignee = ticket.assignee or "-"
        table.add_row(
            ref.project,
            f"{ref.id:03d}",
            ticket.title or "-",
            ticket.status or "-",
            assignee,
            step,
            ticket.mode,
        )
        rows += 1

    if rows == 0:
        typer.echo("(no tasks)")
        return

    Console().print(table)
