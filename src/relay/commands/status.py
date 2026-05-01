"""`relay status` — one line per task in the repo."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from relay.config import ConfigError, load_config
from relay.tasks import list_tasks, read_ticket
from relay.ticket import TicketError


def status() -> None:
    """Show tasks in the repo."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    refs = list_tasks(cfg)
    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    # Slugs can be long; don't let rich wrap them mid-string in narrow terminals.
    table.add_column("slug", no_wrap=True, overflow="fold")
    for col in ("title", "status", "assignee", "step", "mode"):
        table.add_column(col)

    rows = 0
    for ref in refs:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        step = ticket.step or "-"
        assignee = ticket.assignee or "-"
        table.add_row(
            ref.slug,
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
