"""`coga megalaunch` — sequentially attempt launchable work.

Three ways in, one engine:

- bare `coga megalaunch` — sweep every launchable `active` or `in_progress`
  task (`active` starts, `in_progress` resumes).
- `coga megalaunch --pick` — arrow-key picker over every task worth launching
  (any owner, any status but `done`, drafts included), nothing pre-checked;
  the confirmed set runs staged — prepare (a batch prompt offers to author
  picked drafts) → activate → launch — as an explicit selection (and is saved
  for `--relaunch`).
- `coga megalaunch --relaunch` — replay the last confirmed selection.
"""

from __future__ import annotations

import os
import select
import sys
import termios
import tty

import typer
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.text import Text

from coga import notification
from coga.commands.launch import _interactive_stdio_has_tty
from coga.config import Config, ConfigError, load_config
from coga.megalaunch import (
    MegalaunchError,
    MegalaunchRun,
    launchable_candidates,
    load_selection,
    render_run_summary,
    run_megalaunch,
    save_selection,
)
from coga.tasks import TaskRef, UnknownDirectoryError, list_tasks, read_ticket
from coga.ticket import Ticket, TicketError


def megalaunch(
    directory: str | None = typer.Argument(
        None,
        metavar="[DIR]",
        help=(
            "Only sweep (or pick from) tasks under `tasks/<DIR>/` (a "
            "directory path, nested ones included, e.g. `marketing` or "
            "`marketing/social`), same as `coga status <DIR>`. Omit to "
            "cover every task."
        ),
    ),
    pick: bool = typer.Option(
        False,
        "--pick",
        help=(
            "Choose interactively: an arrow-key list of every task worth "
            "launching (any owner, any status but done, drafts included), "
            "nothing pre-checked; the confirmed set is prepared (a batch "
            "prompt offers to run the authoring interview on picked drafts), "
            "activated, then launched, and is saved for --relaunch."
        ),
    ),
    relaunch: bool = typer.Option(
        False,
        "--relaunch",
        help="Re-run the last confirmed picker selection.",
    ),
    max_tasks: int | None = typer.Option(
        None,
        "--max-tasks",
        min=1,
        help="Stop after this many launchable tasks have been attempted.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help=(
            "Launch swept tasks with this configured agent type regardless "
            "of each ticket's assignee (ephemeral override, same as "
            "`coga launch --agent`; human-assigned tickets still skip)."
        ),
    ),
) -> None:
    """Run the shared megalaunch engine once."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    if agent is not None:
        try:
            cfg.agent_type(agent)
        except ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            sys.exit(2)

    try:
        selection = _resolve_selection(cfg, directory, pick=pick, relaunch=relaunch)
    except (MegalaunchError, UnknownDirectoryError, ConfigError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    if selection is not None and not selection:
        # The picker (or an empty candidate list) already said why.
        return

    # A picked selection that includes drafts gets one batch question: run the
    # guided authoring interview on them first, or launch what's ready and let
    # the not-ready drafts report themselves. Only asked when there's a draft
    # to author, so a pick of ready work is never interrupted.
    author_drafts = _confirm_author_drafts(cfg, selection) if selection else False

    try:
        run = run_megalaunch(
            cfg,
            max_tasks=max_tasks,
            agent_override=agent,
            directory=directory,
            selection=selection,
            author_drafts=author_drafts,
        )
    except (MegalaunchError, UnknownDirectoryError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    # Local outcome to stdout before the notification post, so a Slack crash
    # still leaves the run summary visible (coga/sync convention).
    typer.echo(render_run_summary(run))
    message = _drain_post_text(run)
    if message is not None:
        notification.post(cfg, message)
    if run.counts["failed"]:
        sys.exit(1)


def _confirm_author_drafts(cfg: Config, selection: list[str]) -> bool:
    """Ask once whether to author the picked drafts, or `False` if none.

    A picked `draft` is not-yet-ready work: authoring it (the guided
    `coga ticket` interview) is what makes it launchable. But forcing an
    interview on every pick is heavy, so this is a single opt-in prompt raised
    only when the confirmed selection actually contains a draft — a pick of
    ready work is never interrupted.
    """
    wanted = set(selection)
    drafts = [
        ref.id_slug
        for ref in list_tasks(cfg)
        if ref.id_slug in wanted and _is_draft(ref)
    ]
    if not drafts:
        return False
    noun = "draft" if len(drafts) == 1 else "drafts"
    return typer.confirm(
        f"{len(drafts)} picked {noun} ({', '.join(sorted(drafts))}) — run the "
        "guided authoring interview to make them ready before launching?",
        default=True,
    )


def _is_draft(ref: TaskRef) -> bool:
    try:
        return read_ticket(ref).status == "draft"
    except TicketError:
        return False


def _resolve_selection(
    cfg: Config,
    directory: str | None,
    *,
    pick: bool,
    relaunch: bool,
) -> list[str] | None:
    """Turn the flags into the engine's `selection`.

    `None` means the non-explicit sweep; an empty list means the human
    confirmed nothing (caller reports and exits cleanly).
    """
    if relaunch and (pick or directory is not None):
        raise MegalaunchError(
            "--relaunch replays the last saved selection; combining it with "
            "--pick or a directory is ambiguous."
        )

    if relaunch:
        return _saved_selection_still_on_disk(cfg)
    if not pick:
        # Default: the non-interactive sweep of launchable active tasks.
        return None

    # --pick: the interactive arrow-key picker over an explicit list.
    if not _interactive_stdio_has_tty():
        raise MegalaunchError(
            "The megalaunch picker is interactive and requires a TTY. "
            "Drop --pick for the non-interactive sweep."
        )
    candidates = launchable_candidates(cfg, directory=directory)
    if not candidates:
        typer.echo("No tasks to pick (any status but done; drafts included).")
        return []
    selection = _pick_selection(candidates)
    if selection:
        save_selection(cfg, selection)
        typer.echo(f"Picked: {', '.join(selection)}")
    else:
        typer.echo("Nothing selected — nothing launched.")
    return selection


def _saved_selection_still_on_disk(cfg: Config) -> list[str]:
    """The saved selection minus tasks that no longer exist, reported loudly."""
    saved = load_selection(cfg)
    existing = {ref.id_slug for ref in list_tasks(cfg)}
    kept = [slug for slug in saved if slug in existing]
    for slug in saved:
        if slug not in existing:
            typer.secho(
                f"Saved selection: {slug} no longer exists — skipped.",
                fg=typer.colors.YELLOW,
                err=True,
            )
    if not kept:
        raise MegalaunchError(
            "None of the saved selection's tasks exist anymore — run the "
            "picker again."
        )
    return kept


def _decode_key(data: bytes) -> str:
    """Map a raw keypress byte sequence to a picker action ('' = ignore)."""
    if data in (b"\x1b[A", b"\x1bOA", b"k"):
        return "up"
    if data in (b"\x1b[B", b"\x1bOB", b"j"):
        return "down"
    if data == b" ":
        return "space"
    if data in (b"\r", b"\n"):
        return "enter"
    if data in (b"q", b"\x1b", b"\x03"):  # q, bare Esc, Ctrl-C
        return "quit"
    if data == b"a":
        return "all"
    if data == b"n":
        return "none"
    return ""


def _read_key() -> str:
    """Read one keypress from the terminal in raw mode, decoded to an action."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        data = os.read(fd, 1)
        if data == b"\x1b":
            # Arrow keys arrive as ESC [ A / ESC O A; a bare Esc sends nothing
            # more, so a short poll distinguishes the two.
            while len(data) < 3 and select.select([fd], [], [], 0.02)[0]:
                data += os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return _decode_key(data)


def _pick_selection(candidates: list[tuple[TaskRef, Ticket]]) -> list[str]:
    """Arrow-key picker: ↑/↓ (or j/k) move, Space toggles, Enter launches.

    Nothing starts checked — the list reaches wide (other owners' tickets,
    drafts, paused, blocked), so every launch is an explicit opt-in. Returns
    the confirmed slugs, or an empty list when the human backed out (`q`/Esc,
    or confirming with nothing checked).
    """
    console = Console()
    cursor = 0
    selected: set[int] = set()
    with Live(
        _picker_view(candidates, selected, cursor, console),
        console=console,
        auto_refresh=False,
        transient=True,
    ) as live:
        while True:
            key = _read_key()
            if key == "quit":
                return []
            if key == "enter":
                return [candidates[i][0].id_slug for i in sorted(selected)]
            if key == "up":
                cursor = (cursor - 1) % len(candidates)
            elif key == "down":
                cursor = (cursor + 1) % len(candidates)
            elif key == "space":
                selected ^= {cursor}
            elif key == "all":
                selected = set(range(len(candidates)))
            elif key == "none":
                selected = set()
            live.update(
                _picker_view(candidates, selected, cursor, console), refresh=True
            )


def _picker_window(total: int, cursor: int, rows: int) -> tuple[int, int]:
    """Half-open [start, end) of candidate indices to show for this cursor.

    Rich's Live crops a taller-than-terminal render to the last screenful, so
    without windowing the top of a long list scrolls off and the cursor can
    sit on an invisible row. We scroll the viewport to keep the cursor inside
    it, leaving a one-row margin at each edge when there is more list to reveal.
    """
    if rows <= 0 or total <= rows:
        return 0, total
    # Anchor the window on the "page" the cursor falls in, then nudge so the
    # cursor is never pinned to the very top/bottom edge while more rows exist.
    start = max(0, min(cursor - rows // 2, total - rows))
    return start, start + rows


def _picker_view(
    candidates: list[tuple[TaskRef, Ticket]],
    selected: set[int],
    cursor: int,
    console: Console,
) -> Group:
    # Reserve rows for the table header, the hint line, and the two possible
    # scroll indicators so the viewport always fits within the terminal.
    rows = max(1, console.size.height - 4)
    start, end = _picker_window(len(candidates), cursor, rows)

    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    table.add_column("")
    table.add_column("sel")
    table.add_column("slug")
    table.add_column("status")
    table.add_column("owner")
    table.add_column("step")
    table.add_column("title")
    for index in range(start, end):
        ref, ticket = candidates[index]
        table.add_row(
            Text("❯" if index == cursor else " "),
            # Text, not str: a bare "[x]" would be eaten as Rich markup.
            Text("[x]" if index in selected else "[ ]"),
            ref.id_slug,
            ticket.status,
            ticket.owner or "-",
            ticket.step or "-",
            ticket.title,
            style="reverse" if index == cursor else None,
        )
    parts: list[Text | Table] = []
    if start > 0:
        parts.append(Text(f"  ↑ {start} more above", style="dim"))
    parts.append(table)
    if end < len(candidates):
        parts.append(Text(f"  ↓ {len(candidates) - end} more below", style="dim"))
    parts.append(
        Text(
            "↑/↓ move · Space toggle · a all · n none · Enter launch · q quit",
            style="dim",
        )
    )
    return Group(*parts)


def _drain_post_text(run: MegalaunchRun) -> str | None:
    """One live line: what was drained.

    Silent when the run had no results at all — an empty repo is lifecycle
    noise, not an outcome a teammate needs within minutes.
    """
    if not run.results:
        return None
    counts = run.counts
    launched = [result.slug for result in run.results if result.launched]
    parts = [
        "launched " + ", ".join(f"*{slug}*" for slug in launched)
        if launched
        else "nothing launched"
    ]
    not_launchable = (
        counts["skipped-unresolved-blocker"]
        + counts["skipped-human-gate"]
        + counts["skipped-unlaunchable"]
    )
    if not_launchable:
        parts.append(f"{not_launchable} not launchable")
    if counts["failed"]:
        parts.append(f"{counts['failed']} failed")
    scope = [run.directory] if run.directory is not None else []
    if run.agent_override is not None:
        scope.append(f"as {run.agent_override}")
    if run.selection is not None:
        scope.append("selected")
    label = f"Megalaunch drain ({', '.join(scope)})" if scope else "Megalaunch drain"
    return label + ": " + "; ".join(parts)
