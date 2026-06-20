"""`relay status` — one line per task in the repo."""

from __future__ import annotations

import sys
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from relay.config import ConfigError, load_config
from relay.logfile import last_activity
from relay.tasks import (
    UnknownDirectoryError,
    filter_tasks_under,
    is_under,
    list_tasks,
    read_ticket,
)
from relay.ticket import TicketError

# Below this terminal width Rich's column balancer can fold long values
# one-char-per-line, which makes the output unreadable in tmux split panes
# and small windows. Switch every column to no-wrap + ellipsis so each task
# stays on a single line.
NARROW_WIDTH = 100

ORDER_BY_CHOICES = ("slug", "status", "owner", "assignee", "step", "mode", "updated")


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
        help="Include tasks whose status is `done` (hidden by default).",
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

    # `status` is strictly read-only: it never hits the network or mutates
    # ticket state as a side effect of rendering (principle 6, fail loud,
    # names `status`/`show`/`validate` as forbidden mutators). Catching up
    # merged PRs is the job of the `autoclose-merged` recurring sweep.
    refs = list_tasks(cfg)
    try:
        refs = filter_tasks_under(refs, directory, cfg, recurse=not no_recurse)
    except UnknownDirectoryError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    console = Console()
    narrow = console.width < NARROW_WIDTH

    rows = []
    hidden_done = 0
    for ref in refs:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if not show_all and ticket.status == "done":
            hidden_done += 1
            continue
        rows.append({
            "slug": ref.id_slug,
            "directory": ref.directory,
            "status": ticket.status or "-",
            "owner": ticket.owner or "-",
            "assignee": ticket.assignee or "-",
            "step": ticket.step or "-",
            "mode": ticket.mode,
            "updated_ts": last_activity(ref.path),
        })

    # Default reading is "newest first" for date columns and alphabetical
    # for everything else; --reverse flips whichever default applies.
    descending = (order_by == "updated") ^ reverse

    if order_by == "updated":
        # Two passes so the "missing" bucket always ends up last regardless
        # of direction. Pass 1: sort by the timestamp itself, with None
        # mapped to datetime.min so it doesn't crash compares. Pass 2 is
        # stable, so it preserves pass-1 order within each bucket.
        rows.sort(key=lambda r: r["updated_ts"] or datetime.min, reverse=descending)
        rows.sort(key=lambda r: r["updated_ts"] is None)
    else:
        rows.sort(key=lambda r: r[order_by], reverse=descending)

    if not rows:
        if directory:
            # The directory exists (an unknown one already failed loud above)
            # but holds no tasks yet — say which, so an empty list isn't
            # mistaken for "no tasks anywhere". --no-recurse means "directly
            # in it", so spell that out too.
            where = f"directly in {directory}" if no_recurse else f"in {directory}"
            typer.echo(f"(no tasks {where}){_done_hint(hidden_done)}")
        elif no_recurse:
            # Top-level slice is empty, but nested tasks may still exist —
            # don't claim "no tasks" outright.
            typer.echo(f"(no top-level tasks){_done_hint(hidden_done)}")
        else:
            typer.echo(f"(no tasks){_done_hint(hidden_done)}")
        return

    now = datetime.now()

    # Recurring period tasks are machine-authored jobs created ahead of
    # execution; peel them into their own table so the main list stays the
    # hand-authored backlog. `relay recurring list` is the schedule-aware view.
    # They live under `tasks/recurring/` (possibly in a deeper sub-directory).
    recurring_rows = [r for r in rows if is_under(r["directory"], "recurring")]
    main_rows = [r for r in rows if not is_under(r["directory"], "recurring")]

    if main_rows:
        console.print(_build_table(main_rows, narrow, now))
        console.print(_summary_line(main_rows), style="dim")
    if recurring_rows:
        if main_rows:
            console.print()
        console.print("Recurring", style="bold")
        console.print(_build_table(recurring_rows, narrow, now))
        console.print(_summary_line(recurring_rows), style="dim")
    if hidden_done:
        console.print(_done_hint(hidden_done).lstrip(), style="dim")


def _done_hint(hidden_done: int) -> str:
    """Trailing note pointing at --all when done tasks were filtered out."""
    if not hidden_done:
        return ""
    noun = "done task" if hidden_done == 1 else "done tasks"
    return f"  ({hidden_done} {noun} hidden — use --all to show)"


def _build_table(rows: list[dict], narrow: bool, now: datetime) -> Table:
    """Build one status table from already-sorted rows."""
    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    if narrow:
        # Slug is the primary identifier; pin its column to the longest slug
        # so Rich's balancer doesn't crop it. Everything else ellipsizes.
        max_slug = max((len(r["slug"]) for r in rows), default=0)
        table.add_column("slug", no_wrap=True, overflow="fold", min_width=max_slug)
        for col in ("status", "owner", "assignee", "step", "mode", "updated"):
            table.add_column(col, no_wrap=True, overflow="ellipsis")
    else:
        table.add_column("slug", no_wrap=True, overflow="fold")
        for col in ("status", "owner", "assignee", "step", "mode", "updated"):
            table.add_column(col)

    for r in rows:
        ts = r["updated_ts"]
        updated = _format_relative(ts, now) if ts is not None else "-"
        table.add_row(
            r["slug"], r["status"], r["owner"], r["assignee"],
            r["step"], r["mode"], updated,
        )
    return table


def _summary_line(rows: list[dict]) -> str:
    """Totals line for a table — canonical statuses first, then any others."""
    # Canonical statuses first in fixed order, then any other values seen
    # (e.g. "-" for tickets missing a status field) sorted for stability.
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    canonical = ("in_progress", "active", "draft", "paused", "done")
    parts = [f"{counts[s]} {s}" for s in canonical if counts.get(s)]
    parts += [
        f"{counts[s]} {s}"
        for s in sorted(counts)
        if s not in canonical
    ]
    label = "task" if len(rows) == 1 else "tasks"
    summary = f"{len(rows)} {label}"
    if parts:
        summary += "  ·  " + " · ".join(parts)
    return summary
