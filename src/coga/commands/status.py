"""`coga status` — one line per task in the repo."""

from __future__ import annotations

import sys
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from coga.blackboard import Blocker, open_blockers
from coga.config import ConfigError, load_config
from coga.logfile import last_activity_map
from coga.taskfile import TaskFileError
from coga.tasks import (
    UnknownDirectoryError,
    filter_tasks_under,
    is_under,
    list_task_dirs,
    list_tasks,
    read_ticket,
)
from coga.ticket import TicketError

# Below this terminal width Rich's column balancer can fold long values
# one-char-per-line, which makes the output unreadable in tmux split panes
# and small windows. Switch every column to no-wrap + ellipsis so each task
# stays on a single line.
NARROW_WIDTH = 100

ORDER_BY_CHOICES = ("slug", "status", "owner", "assignee", "step", "autonomy", "updated")


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
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    if dirs:
        _list_dirs(cfg, directory, no_recurse=no_recurse)
        return

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

    # One pass over the global log builds every task's last-activity timestamp,
    # instead of re-scanning a per-task log file for each row.
    activity = last_activity_map(cfg)

    rows = []
    blocked_rows = []
    hidden_done = 0
    for ref in refs:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        blockers = _safe_open_blockers(ref.ticket_path)
        if ticket.status == "blocked" or blockers:
            blocked_rows.append({
                "slug": ref.id_slug,
                "status": ticket.status or "-",
                "owner": ticket.owner or "-",
                "assignee": ticket.assignee or "-",
                "step": ticket.step or "-",
                "blockers": blockers,
            })
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
            "autonomy": ticket.autonomy,
            "updated_ts": activity.get(ref.id_slug),
        })

    if blocked:
        _print_blocked(console, blocked_rows)
        return

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
    # hand-authored backlog. `coga recurring list` is the schedule-aware view.
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
    # Surface the open blocker asks inline so the default triage view answers
    # "what's waiting on me?" without a second `--blocked` command. The task
    # tables already show a `blocked` row; this adds the reason + next step.
    if blocked_rows:
        console.print()
        _print_open_blockers(console, blocked_rows)
    if hidden_done:
        console.print(_done_hint(hidden_done).lstrip(), style="dim")


def _list_dirs(cfg, directory: str | None, *, no_recurse: bool) -> None:
    """Print the plain (non-task) directories under tasks/, one path per line.

    Mirrors the two axes of the task listing: `directory` narrows to the
    sub-tree below a directory (the directory itself is not echoed — it's the
    query, not a result), and `no_recurse` keeps only the immediate level.
    An unknown `directory` fails loud, exactly like the task path.
    """
    available = list_task_dirs(cfg)
    target = directory.strip("/") if directory is not None else None
    if target is not None and target not in available:
        typer.secho(str(UnknownDirectoryError(target, available)),
                    fg=typer.colors.RED, err=True)
        sys.exit(2)

    if target is None:
        selected = list(available)
        base_depth = 0
    else:
        selected = [d for d in available if d.startswith(target + "/")]
        base_depth = target.count("/") + 1

    if no_recurse:
        selected = [d for d in selected if d.count("/") == base_depth]

    if not selected:
        where = f" under {target}" if target else ""
        scope = " immediately" if no_recurse else ""
        typer.echo(f"(no{scope} directories{where})")
        return
    for d in selected:
        typer.echo(d)


def _done_hint(hidden_done: int) -> str:
    """Trailing note pointing at --all when done tasks were filtered out."""
    if not hidden_done:
        return ""
    noun = "done task" if hidden_done == 1 else "done tasks"
    return f"  ({hidden_done} {noun} hidden — use --all to show)"


def _safe_open_blockers(ticket_path) -> list[Blocker]:
    """Best-effort blocker read for a read-only status view."""
    try:
        return open_blockers(ticket_path)
    except (FileNotFoundError, TaskFileError):
        return []


def _build_table(rows: list[dict], narrow: bool, now: datetime) -> Table:
    """Build one status table from already-sorted rows."""
    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    if narrow:
        # Slug is the primary identifier; pin its column to the longest slug
        # so Rich's balancer doesn't crop it. Everything else ellipsizes.
        max_slug = max((len(r["slug"]) for r in rows), default=0)
        table.add_column("slug", no_wrap=True, overflow="fold", min_width=max_slug)
        for col in ("status", "owner", "assignee", "step", "autonomy", "updated"):
            table.add_column(col, no_wrap=True, overflow="ellipsis")
    else:
        table.add_column("slug", no_wrap=True, overflow="fold")
        for col in ("status", "owner", "assignee", "step", "autonomy", "updated"):
            table.add_column(col)

    for r in rows:
        ts = r["updated_ts"]
        updated = _format_relative(ts, now) if ts is not None else "-"
        table.add_row(
            r["slug"], r["status"], r["owner"], r["assignee"],
            r["step"], r["autonomy"], updated,
        )
    return table


def _summary_line(rows: list[dict]) -> str:
    """Totals line for a table — canonical statuses first, then any others."""
    # Canonical statuses first in fixed order, then any other values seen
    # (e.g. "-" for tickets missing a status field) sorted for stability.
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    canonical = ("in_progress", "blocked", "active", "draft", "paused", "done")
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


def _expand_blockers(rows: list[dict]) -> list[dict]:
    """One entry per open blocker ask; a blocked row with none yields one."""
    expanded: list[dict] = []
    for row in rows:
        blockers: list[Blocker] = row["blockers"]
        if blockers:
            for blocker in blockers:
                expanded.append({**row, "blocker": blocker})
        else:
            expanded.append({**row, "blocker": None})
    return expanded


def _print_open_blockers(console: Console, rows: list[dict]) -> None:
    """Print the compact 'Open blockers:' bullet list — one line per ask."""
    console.print("Open blockers:", style="bold")
    for row in _expand_blockers(rows):
        blocker: Blocker | None = row["blocker"]
        reason = (
            blocker.reason
            if blocker is not None
            else "(blocked; no open blocker recorded)"
        )
        console.print(
            f"- {row['slug']}: {reason} "
            f"(next: coga unblock {row['slug']} --answer \"...\")"
        )


def _print_blocked(console: Console, rows: list[dict]) -> None:
    """Print one row per open blocker, so every ask is visible at a glance."""
    now = datetime.now()
    expanded = _expand_blockers(rows)

    if not expanded:
        console.print("(no blocked tasks)")
        return

    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    for col in ("slug", "status", "step", "owner", "assignee", "age", "blocker", "next"):
        table.add_column(col, no_wrap=(col != "blocker"), overflow="fold")

    for row in expanded:
        blocker: Blocker | None = row["blocker"]
        age = "-"
        reason = "(blocked; no open blocker recorded)"
        if blocker is not None:
            if blocker.created_at is not None:
                age = _format_relative(blocker.created_at, now)
            reason = blocker.reason
        table.add_row(
            row["slug"],
            row["status"],
            row["step"],
            row["owner"],
            row["assignee"],
            age,
            reason,
            f"coga unblock {row['slug']} --answer \"...\"",
        )
    console.print(table)
    _print_open_blockers(console, rows)
    console.print(_summary_line(rows), style="dim")
