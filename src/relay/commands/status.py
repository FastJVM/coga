"""`relay status` — one line per task in the repo."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from relay.config import ConfigError, load_config
from relay.tasks import list_tasks, read_ticket
from relay.ticket import TicketError

# Below this terminal width Rich's column balancer can fold long values
# one-char-per-line, which makes the output unreadable in tmux split panes
# and small windows. Switch every column to no-wrap + ellipsis so each task
# stays on a single line.
NARROW_WIDTH = 100


def status() -> None:
    """Show tasks in the repo."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    refs = list_tasks(cfg)
    console = Console()
    narrow = console.width < NARROW_WIDTH

    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    if narrow:
        # Slug is the primary identifier; pin its column to the longest slug
        # so Rich's balancer doesn't crop it. Everything else ellipsizes.
        max_slug = max((len(r.slug) for r in refs), default=0)
        table.add_column("slug", no_wrap=True, overflow="fold", min_width=max_slug)
        for col in ("status", "assignee", "step", "mode"):
            table.add_column(col, no_wrap=True, overflow="ellipsis")
    else:
        # Slugs can be long; don't let rich wrap them mid-string.
        table.add_column("slug", no_wrap=True, overflow="fold")
        for col in ("status", "assignee", "step", "mode"):
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
            ticket.status or "-",
            assignee,
            step,
            ticket.mode,
        )
        rows += 1

    if rows == 0:
        typer.echo("(no tasks)")
        return

    console.print(table)
