"""Rendering for the read-only views (`coga show`, `coga status`).

The command heads in `commands/show.py` / `commands/status.py` stay thin — they
parse Typer args, `load_config()`, and translate errors to `sys.exit(2)`. All of
the actual rendering lives here as reusable, unit-testable, `typer`-free Python,
so it can also run in script-step shape (the `coga/show` skill's `run.py`),
mirroring how `coga.authoring` / `coga.autoclose` keep their substance out of the
command files and raise typed errors instead of exiting.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Mapping

from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from rich.table import Table

from coga.blackboard import Blocker, open_blockers
from coga.config import Config, load_config
from coga.git import stale_coga_task_rels
from coga.logfile import (
    first_activity_map,
    last_activity_map,
    task_log_lines,
)
from coga.taskfile import TaskFileError
from coga.tasks import (
    BootstrapRef,
    UnknownDirectoryError,
    filter_tasks_under,
    is_under,
    list_task_dirs,
    list_tasks,
    read_ticket,
    resolve_target,
)
from coga.ticket import TicketError

# Env var carrying the single target slug for the `coga/show` script skill —
# the script-step channel for the operand the Typer command takes as `<task>`.
VIEW_TARGET_ENV = "COGA_VIEW_TARGET"

# Below this terminal width Rich's column balancer can fold long values
# one-char-per-line, which makes the output unreadable in tmux split panes
# and small windows. Switch every column to no-wrap + ellipsis so each task
# stays on a single line.
NARROW_WIDTH = 100

ORDER_BY_CHOICES = (
    "slug",
    "status",
    "owner",
    "assignee",
    "step",
    "mode",
    "updated",
    "created",
)


class ViewError(Exception):
    """A read view could not render for a reason the caller maps to exit 2."""


# --- show ------------------------------------------------------------------


def render_show(cfg: Config, task: str, console: Console | None = None) -> None:
    """Print a task's contents — its single-file ticket (frontmatter + body +
    blackboard) and, for a real task, its history reconstructed from the
    repo-global log.

    Raises `TaskNotFoundError` when the target cannot be resolved; the caller
    translates that to `sys.exit(2)`.
    """
    ref = resolve_target(cfg, task)

    if console is None:
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
    console.print(Rule(f"{ref.id_slug} — log (from coga/log.md)"))
    console.print()
    lines = task_log_lines(cfg, ref.id_slug)
    if not lines:
        console.print("[dim](no log entries)[/dim]")
    else:
        for line in lines:
            console.print(line)


def render_show_from_env(
    cfg: Config | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Render `show` using the script-skill environment contract.

    The single operand `coga show` takes as `<task>` arrives via
    `COGA_VIEW_TARGET`, mirroring how `finalize_authored_from_env` reads its
    ref from the environment for the `coga/ticket/finalize` skill.
    """
    env = environ if environ is not None else os.environ
    target = env.get(VIEW_TARGET_ENV)
    if not target:
        raise ViewError(f"missing required env var: {VIEW_TARGET_ENV}")
    loaded_cfg = cfg if cfg is not None else load_config()
    render_show(loaded_cfg, target)


# --- status ----------------------------------------------------------------


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
    _warn_if_control_ahead(cfg)

    if dirs:
        _list_dirs(cfg, directory, no_recurse=no_recurse)
        return

    if order_by not in ORDER_BY_CHOICES:
        raise ViewError(
            f"--order-by must be one of: {', '.join(ORDER_BY_CHOICES)}"
        )

    # `status` is strictly read-only: it never hits the network or mutates
    # ticket state as a side effect of rendering (principle 6, fail loud,
    # names `status`/`show`/`validate` as forbidden mutators). Catching up
    # merged PRs is the job of the `autoclose-merged` recurring sweep.
    refs = list_tasks(cfg)
    refs = filter_tasks_under(refs, directory, cfg, recurse=not no_recurse)
    if console is None:
        console = Console()
    narrow = console.width < NARROW_WIDTH

    # One pass over the global log builds every task's last-activity timestamp,
    # instead of re-scanning a per-task log file for each row.
    activity = last_activity_map(cfg)
    # Creation timestamps (earliest log line per ref) — the exact order the
    # megalaunch drain services tickets in. Only needed for this sort column.
    created = first_activity_map(cfg) if order_by == "created" else {}

    rows = []
    blocked_rows = []
    hidden_done = 0
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
            "updated_ts": activity.get(ref.id_slug),
            "created_ts": created.get(ref.id_slug),
        })

    if blocked:
        _print_blocked(console, blocked_rows)
        return

    # Default reading is "newest first" for `updated` and alphabetical for
    # everything else; --reverse flips whichever default applies. `created`
    # defaults to oldest-first — it exists to show the exact order the
    # megalaunch drain services tickets in.
    descending = (order_by == "updated") ^ reverse

    if order_by in ("updated", "created"):
        ts_key = f"{order_by}_ts"
        # Two passes so the "missing" bucket always ends up last regardless
        # of direction. Pass 1: sort by the timestamp itself, with None
        # mapped to datetime.min so it doesn't crash compares. Pass 2 is
        # stable, so it preserves pass-1 order within each bucket.
        rows.sort(key=lambda r: r[ts_key] or datetime.min, reverse=descending)
        rows.sort(key=lambda r: r[ts_key] is None)
    else:
        rows.sort(key=lambda r: r[order_by], reverse=descending)

    if not rows:
        if directory:
            # The directory exists (an unknown one already failed loud above)
            # but holds no tasks yet — say which, so an empty list isn't
            # mistaken for "no tasks anywhere". --no-recurse means "directly
            # in it", so spell that out too.
            where = f"directly in {directory}" if no_recurse else f"in {directory}"
            print(f"(no tasks {where}){_done_hint(hidden_done)}")
        elif no_recurse:
            # Top-level slice is empty, but nested tasks may still exist —
            # don't claim "no tasks" outright.
            print(f"(no top-level tasks){_done_hint(hidden_done)}")
        else:
            print(f"(no tasks){_done_hint(hidden_done)}")
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
    if hidden_done:
        console.print(_done_hint(hidden_done).lstrip(), style="dim")


def _warn_if_control_ahead(cfg: Config) -> None:
    """One yellow stderr line when the fetched control ref has newer task state.

    `status` is strictly read-only and no-network (principle 6), so this leans
    on `stale_coga_task_rels`: a comparison against the local remote-tracking
    `origin/<control>` ref only — it can say "your view is stale as of the last
    fetch", never fetch to find out more, and it fails open to silence. Stderr,
    not the table's stdout, so piped output stays parseable.
    """
    stale = stale_coga_task_rels(cfg)
    if not stale:
        return
    noun = "task" if len(stale) == 1 else "tasks"
    Console(stderr=True).print(
        f"[yellow]Warning: {cfg.git_remote}/{cfg.git_control_branch} has newer "
        f"state for {len(stale)} {noun} than this checkout — this view may be "
        f"stale. A finished `coga launch` from here refreshes it.[/yellow]"
    )


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


def _done_hint(hidden_done: int) -> str:
    """Trailing note pointing at --all when done tasks were filtered out."""
    if not hidden_done:
        return ""
    noun = "done task" if hidden_done == 1 else "done tasks"
    return f"  ({hidden_done} {noun} hidden — use --all to show)"


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
