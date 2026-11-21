"""Status report policy, owned by this command ticket."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from coga.blackboard import Blocker, open_blockers
from coga.config import Config, ConfigError, load_config
from coga.logfile import first_activity_map
from coga.lifecycle import STATUS_DISPLAY_ORDER, TERMINAL_STATUSES
from coga.recurring import TemplateStatus, list_templates
from coga.service_order import service_order
from coga.taskfile import TaskFileError
from coga.tasks import (
    UnknownDirectoryError, filter_tasks_under, list_task_dirs, list_tasks, read_ticket,
)
from coga.ticket import TicketError
from coga.views import last_updated_map, operator_cell


NARROW_WIDTH = 100


ORDER_BY_CHOICES = (
    "slug",
    "status",
    "owner",
    "operator",
    "step",
    "updated",
    "created",
)


ORDER_BY_ALIASES = {"assignee": "operator"}




class ViewError(Exception):
    """A read view could not render for a reason the caller maps to exit 2."""


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


def render_status(
    cfg: Config,
    *,
    directory: str | None,
    no_recurse: bool,
    order_by: str,
    reverse: bool,
    show_all: bool,
    dirs: bool,
    blocked: bool,
    console: Console | None = None,
) -> None:
    """Show tasks in the repo.

    Raises `ViewError` for a bad `--order-by` and `UnknownDirectoryError` for an
    unknown directory; the caller translates both to `sys.exit(2)`.
    """

    if dirs:
        _list_dirs(cfg, directory, no_recurse=no_recurse)
        return

    order_by = ORDER_BY_ALIASES.get(order_by, order_by)
    if order_by not in ORDER_BY_CHOICES:
        raise ViewError(
            f"--order-by must be one of: {', '.join(ORDER_BY_CHOICES)}"
        )

    # `status` is strictly read-only: it never hits the network or mutates
    # ticket state as a side effect of rendering (principle 6, fail loud,
    # names `status`/`show`/`validate` as forbidden mutators).
    refs = list_tasks(cfg)
    refs = filter_tasks_under(refs, directory, cfg, recurse=not no_recurse)
    if console is None:
        console = Console()
    narrow = console.width < NARROW_WIDTH

    updated = last_updated_map(cfg, refs)
    # Creation timestamps (earliest log line per ref) — the exact order the
    # megalaunch drain services tickets in. Only needed for this sort column.
    created = first_activity_map(cfg) if order_by == "created" else {}

    rows = []
    blocked_rows = []
    hidden_terminal: dict[str, int] = {}
    for ref in refs:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        # Status is the signal: a ticket is blocked iff its status says so.
        # Leftover blackboard asks on a non-blocked (e.g. finished) ticket are
        # status/blackboard drift for `coga validate` to catch, not this
        # triage view's to re-derive blocked-ness from.
        if ticket.status == "blocked":
            blocked_rows.append({
                "slug": ref.id_slug,
                "status": ticket.status,
                "owner": ticket.owner or "-",
                "step": ticket.step or "-",
                "blockers": _safe_open_blockers(ref.ticket_path),
            })
        if not show_all and ticket.status in TERMINAL_STATUSES:
            hidden_terminal[ticket.status] = hidden_terminal.get(ticket.status, 0) + 1
            continue
        rows.append({
            "slug": ref.id_slug,
            "directory": ref.directory,
            "status": ticket.status or "-",
            "owner": ticket.owner or "-",
            "operator": operator_cell(cfg, ref, ticket),
            "step": ticket.step or "-",
            "updated_ts": updated.get(ref.id_slug),
            "created_ts": created.get(ref.id_slug),
        })

    if blocked:
        _print_blocked(console, blocked_rows)
        return

    # Default reading is "newest first" for `updated` and alphabetical for
    # everything else; --reverse flips whichever default applies.
    descending = (order_by == "updated") ^ reverse

    if order_by == "created":
        # Not a plain timestamp sort: `created` exists to show the exact order
        # the megalaunch drain services tickets in, so it reuses that key
        # wholesale (oldest-first, numbered sub-trees in number order). Rows
        # the loop above dropped simply aren't in the position map.
        position = {
            ref.id_slug: index
            for index, ref in enumerate(service_order(refs, created))
        }
        rows.sort(key=lambda r: position.get(r["slug"], len(position)))
        if reverse:
            rows.reverse()
    elif order_by == "updated":
        ts_key = "updated_ts"
        # Two passes so the "missing" bucket always ends up last regardless
        # of direction. Pass 1: sort by the timestamp itself, with None
        # mapped to datetime.min so it doesn't crash compares. Pass 2 is
        # stable, so it preserves pass-1 order within each bucket.
        rows.sort(key=lambda r: r[ts_key] or datetime.min, reverse=descending)
        rows.sort(key=lambda r: r[ts_key] is None)
    else:
        rows.sort(key=lambda r: r[order_by], reverse=descending)

    now = datetime.now()
    # Templates in `coga/recurring/` aren't tasks yet, so the main table can't
    # carry them; the footer summarizes how many exist and how many are due
    # whenever the view's scope covers `tasks/recurring/`. Instantiated
    # period tasks are ordinary tasks and render in the main table like any
    # other row.
    templates = (
        list_templates(cfg, now)
        if _covers_recurring(directory, no_recurse=no_recurse)
        else []
    )

    if not rows:
        if directory:
            # The directory exists (an unknown one already failed loud above)
            # but holds no tasks yet — say which, so an empty list isn't
            # mistaken for "no tasks anywhere". --no-recurse means "directly
            # in it", so spell that out too.
            where = f"directly in {directory}" if no_recurse else f"in {directory}"
            print(f"(no tasks {where}){_terminal_hint(hidden_terminal)}")
        elif no_recurse:
            # Top-level slice is empty, but nested tasks may still exist —
            # don't claim "no tasks" outright.
            print(f"(no top-level tasks){_terminal_hint(hidden_terminal)}")
        else:
            print(f"(no tasks){_terminal_hint(hidden_terminal)}")
        _print_recurring_templates(console, templates, leading_blank=False)
        return

    console.print(_build_table(rows, narrow, now))
    console.print(_summary_line(rows), style="dim")
    _print_recurring_templates(console, templates, leading_blank=True)
    if hidden_terminal:
        console.print(_terminal_hint(hidden_terminal).lstrip(), style="dim")


def _covers_recurring(directory: str | None, *, no_recurse: bool) -> bool:
    """True when the status filter's scope includes `tasks/recurring/`.

    That's the bare recursive view or a filter on the recurring sub-tree; a
    filter on another directory, or the top-level `--no-recurse` slice, never
    shows recurring period tasks, so the templates footer stays out too.
    """
    if directory is None:
        return not no_recurse
    target = directory.strip("/")
    return target == "recurring" or target.startswith("recurring/")


def _print_recurring_templates(
    console: Console, templates: list[TemplateStatus], *, leading_blank: bool
) -> None:
    """Footer summarizing the `coga/recurring/` templates in one line.

    Templates exist even when no period task is live, so this renders whenever
    templates exist at all — but as counts, not a per-template table: a fresh
    repo with six healthy, never-instantiated templates gets one line pointing
    at `coga recurring list`, the full schedule-aware view. Only the templates
    the summary would otherwise hide something about are named: one that
    failed to load (`error`) and one whose instance ticket is unreadable
    (`instance_status == "unknown"`), each on its own line, sorted by name.
    `due` is `TemplateStatus.due` — template-period state, not a count of
    launchable tasks.
    """
    # Disabled and unselected bundled jobs are not scheduled; the full
    # `coga recurring list` view names them with their reason.
    templates = [s for s in templates if s.error or s.selection == "enabled"]
    if not templates:
        return
    if leading_blank:
        console.print()
    ordered = sorted(templates, key=lambda x: x.name)
    errors = [s for s in ordered if s.error]
    unknown = [s for s in ordered if not s.error and s.instance_status == "unknown"]
    due = sum(1 for s in ordered if s.due)
    parts = [
        _count_noun(len(ordered), "template"),
        f"{due} due",
    ]
    if errors:
        parts.append(f"[red]{_count_noun(len(errors), 'error')}[/red]")
    console.print(
        f"[bold]Recurring:[/bold] {' · '.join(parts)} — coga recurring list"
    )
    for s in errors:
        console.print(f"  [red]error: {s.name} — {s.error}[/red]")
    for s in unknown:
        instance = s.instance.id_slug if s.instance is not None else s.target_slug
        console.print(
            f"  [yellow]warning: {s.name} — instance {instance} is unreadable "
            "(status unknown)[/yellow]"
        )


def _count_noun(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _list_dirs(cfg: Config, directory: str | None, *, no_recurse: bool) -> None:
    """Print the plain (non-task) directories under tasks/, one path per line.

    Mirrors the two axes of the task listing: `directory` narrows to the
    sub-tree below a directory (the directory itself is not echoed — it's the
    query, not a result), and `no_recurse` keeps only the immediate level.
    An unknown `directory` fails loud, exactly like the task path.
    """
    available = list_task_dirs(cfg)
    target = directory.strip("/") if directory is not None else None
    if target is not None and target not in available:
        raise UnknownDirectoryError(target, available)

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
        print(f"(no{scope} directories{where})")
        return
    for d in selected:
        print(d)


def _terminal_hint(hidden: Mapping[str, int]) -> str:
    """Trailing note pointing at ``--all`` for filtered terminal tasks."""
    total = sum(hidden.values())
    if not total:
        return ""
    present = [(status, hidden.get(status, 0)) for status in ("done", "canceled")]
    present = [(status, count) for status, count in present if count]
    if len(present) == 1:
        status, count = present[0]
        noun = f"{status} task" if count == 1 else f"{status} tasks"
        return f"  ({count} {noun} hidden — use --all to show)"
    breakdown = ", ".join(f"{count} {status}" for status, count in present)
    noun = "terminal task" if total == 1 else "terminal tasks"
    return (
        f"  ({total} {noun} hidden: {breakdown} — use --all to show)"
    )


def _safe_open_blockers(ticket_path: Path) -> list[Blocker]:
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
        for col in ("status", "owner", "operator", "step", "updated"):
            table.add_column(col, no_wrap=True, overflow="ellipsis")
    else:
        table.add_column("slug", no_wrap=True, overflow="fold")
        for col in ("status", "owner", "operator", "step", "updated"):
            table.add_column(col)

    for r in rows:
        ts = r["updated_ts"]
        updated = _format_relative(ts, now) if ts is not None else "-"
        table.add_row(
            r["slug"], r["status"], r["owner"], r["operator"],
            r["step"], updated,
        )
    return table


def _summary_line(rows: list[dict]) -> str:
    """Totals line for a table — canonical statuses first, then any others."""
    # Canonical statuses first in fixed order, then any other values seen
    # (e.g. "-" for tickets missing a status field) sorted for stability.
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    parts = [f"{counts[s]} {s}" for s in STATUS_DISPLAY_ORDER if counts.get(s)]
    parts += [
        f"{counts[s]} {s}"
        for s in sorted(counts)
        if s not in STATUS_DISPLAY_ORDER
    ]
    label = "task" if len(rows) == 1 else "tasks"
    summary = f"{len(rows)} {label}"
    if parts:
        summary += "  ·  " + " · ".join(parts)
    return summary


def _print_blocked(console: Console, rows: list[dict]) -> None:
    """Print one row per open blocker, so every ask is visible at a glance."""
    now = datetime.now()
    expanded: list[dict] = []
    for row in rows:
        blockers: list[Blocker] = row["blockers"]
        if blockers:
            for blocker in blockers:
                expanded.append({**row, "blocker": blocker})
        else:
            expanded.append({**row, "blocker": None})

    if not expanded:
        console.print("(no blocked tasks)")
        return

    # Fixed widths on every column but the reason, then the reason is
    # pre-truncated to whatever width is left. A `no_wrap` column reports its
    # full text as its minimum width, so a long un-truncated reason would make
    # Rich collapse the short columns to zero to fit it; capping the text up
    # front keeps every cell within its column and the table within the
    # terminal. Full reason text is one `coga show <slug>` away.
    slug_w, step_w, owner_w, age_w = 30, 10, 8, 4
    # Conservative overhead (padding 2/col + separators), rounded up so the
    # budget stays a touch under what's really free — then Rich never has to
    # shrink the reason column further and re-clip our text.
    overhead = 2 * 5 + 4
    reason_w = max(10, console.width - (slug_w + step_w + owner_w + age_w) - overhead)

    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    table.add_column("slug", no_wrap=True, overflow="ellipsis", width=slug_w)
    table.add_column("step", no_wrap=True, overflow="ellipsis", width=step_w)
    table.add_column("owner", no_wrap=True, overflow="ellipsis", width=owner_w)
    table.add_column("age", no_wrap=True, width=age_w)
    table.add_column("reason", no_wrap=True)

    for row in expanded:
        blocker: Blocker | None = row["blocker"]
        age = "-"
        reason = "(no open blocker recorded)"
        if blocker is not None:
            if blocker.created_at is not None:
                age = _format_relative(blocker.created_at, now)
            # Collapse internal whitespace to one line, then clip to fit.
            reason = " ".join(blocker.reason.split())
        if len(reason) > reason_w:
            reason = reason[: reason_w - 1] + "…"
        table.add_row(row["slug"], row["step"], row["owner"], age, reason)

    console.print(table)
    console.print(_summary_line(rows), style="dim")
    # The unblock command is identical bar the slug (already in the table), so
    # it's a shared footer, not a repeated column — signal over boilerplate.
    console.print(
        'Answer:  coga unblock <slug> --answer "..."'
        "     Full reason:  coga show <slug>",
        style="dim",
    )


app = typer.Typer(add_completion=False)


@app.command()
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
        help=(
            f"Sort column. One of: {', '.join(ORDER_BY_CHOICES)} "
            f"(aliases: {', '.join(ORDER_BY_ALIASES)}). `operator` sorts the "
            "column derived from each ticket's current workflow step — it is a "
            "read-only view, not an assignment."
        ),
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


if __name__ == "__main__":
    app(prog_name="coga status")
