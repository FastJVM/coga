"""`relay status` — one line per task in the repo."""

from __future__ import annotations

import sys
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from relay.automerge import auto_bump_merged
from relay.config import ConfigError, load_config
from relay.logfile import last_activity
from relay.tasks import list_tasks, read_ticket
from relay.ticket import TicketError

# Below this terminal width Rich's column balancer can fold long values
# one-char-per-line, which makes the output unreadable in tmux split panes
# and small windows. Switch every column to no-wrap + ellipsis so each task
# stays on a single line.
NARROW_WIDTH = 100

ORDER_BY_CHOICES = ("slug", "status", "assignee", "step", "mode", "updated")


def _format_relative(then: datetime, now: datetime) -> str:
    """Compact relative time (`5m`, `3h`, `2d`, `4w`)."""
    delta = now - then
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "0m"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    if days < 7:
        return f"{days}d"
    return f"{days // 7}w"


def status(
    order_by: str = typer.Option(
        "updated",
        "--order-by",
        "-o",
        help=f"Sort column. One of: {', '.join(ORDER_BY_CHOICES)}.",
    ),
    reverse: bool = typer.Option(
        False, "--reverse", "-r", help="Reverse sort order."
    ),
) -> None:
    """Show tasks in the repo."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    if order_by not in ORDER_BY_CHOICES:
        typer.secho(
            f"--order-by must be one of: {', '.join(ORDER_BY_CHOICES)}",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # Opportunistic auto-bump pass: if a teammate merged a PR while this
    # machine was idle, catch up before rendering. quiet=True swallows
    # `gh` errors (missing/unauthed) so a fast command stays fast — the
    # explicit `relay automerge` path surfaces those failures normally.
    auto_bump_merged(cfg, quiet=True)

    refs = list_tasks(cfg)
    console = Console()
    narrow = console.width < NARROW_WIDTH

    rows = []
    for ref in refs:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        rows.append({
            "slug": ref.slug,
            "status": ticket.status or "-",
            "assignee": ticket.assignee or "-",
            "step": ticket.step or "-",
            "mode": ticket.mode,
            "updated_ts": last_activity(ref.path),
        })

    # Default reading is "newest first" for date columns and alphabetical
    # for everything else; --reverse flips whichever default applies.
    descending = (order_by == "updated") ^ reverse

    if order_by == "updated":
        # Two passes so the "missing" group always ends up last regardless
        # of direction. Pass 1: sort by the timestamp itself, with None
        # mapped to datetime.min so it doesn't crash compares. Pass 2 is
        # stable, so it preserves pass-1 order within each group.
        rows.sort(key=lambda r: r["updated_ts"] or datetime.min, reverse=descending)
        rows.sort(key=lambda r: r["updated_ts"] is None)
    else:
        rows.sort(key=lambda r: r[order_by], reverse=descending)

    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    if narrow:
        # Slug is the primary identifier; pin its column to the longest slug
        # so Rich's balancer doesn't crop it. Everything else ellipsizes.
        max_slug = max((len(r["slug"]) for r in rows), default=0)
        table.add_column("slug", no_wrap=True, overflow="fold", min_width=max_slug)
        for col in ("status", "assignee", "step", "mode", "updated"):
            table.add_column(col, no_wrap=True, overflow="ellipsis")
    else:
        table.add_column("slug", no_wrap=True, overflow="fold")
        for col in ("status", "assignee", "step", "mode", "updated"):
            table.add_column(col)

    now = datetime.now()
    for r in rows:
        ts = r["updated_ts"]
        updated = _format_relative(ts, now) if ts is not None else "-"
        table.add_row(
            r["slug"], r["status"], r["assignee"], r["step"], r["mode"], updated,
        )

    if not rows:
        typer.echo("(no tasks)")
        return

    console.print(table)
