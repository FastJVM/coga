"""Terminal multi-select picker, shared by `megalaunch --pick` and `coga init`.

The engine half of the split that `src/coga/<name>.py` plus
`src/coga/commands/<name>.py` follows elsewhere: this module owns the input
loops and the rendering, and each command owns the adapter that builds rows
and interprets the answer.

Two input paths, dispatched on `os.name` at call time:

- POSIX gets the arrow-key loop (`termios`/`tty`/`select` plus `rich.Live`).
- Anything else gets `_pick_numbered`, which reads through `typer.prompt` and
  touches no POSIX-only module. `coga init` has to ask its question on
  Windows; `megalaunch --pick` picks this path up incidentally.

Dispatching at call time rather than import time is what lets a POSIX test
reach the numbered path.
"""

from __future__ import annotations

import os

if os.name == "posix":
    import select
    import termios
    import tty

import signal
import sys
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field

import typer
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.text import Text


@dataclass(frozen=True)
class PickerRow:
    """One selectable row: `key` is what `pick` returns, `cells` what it draws."""

    key: str
    cells: tuple[str, ...]


@dataclass(frozen=True)
class PickerColumn:
    """One data column. `width`/`ratio` pass through to `rich.Table.add_column`.

    Deliberately *not* carrying `no_wrap`/`overflow`: `pick` sets both on every
    column itself, because one-terminal-line-per-row is what the scroll budget
    in `_picker_window` is computed against, not a caller's styling choice.
    """

    header: str
    width: int | None = None
    ratio: int | None = None


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
    if data == b"\x03":
        # Ctrl-C is its own action, not a synonym for `q`. `tty.setraw` clears
        # ISIG, so it arrives as a byte instead of raising KeyboardInterrupt —
        # and the two mean different things to a caller that writes files on
        # quit. `pick` turns this back into the KeyboardInterrupt the terminal
        # would have raised in cooked mode.
        return "cancel"
    if data in (b"q", b"\x1b"):  # q, bare Esc
        return "quit"
    if data == b"a":
        return "all"
    if data == b"n":
        return "none"
    return ""


def _read_key(resize_fd: int) -> str:
    """Read one keypress from the terminal in raw mode, decoded to an action.

    `resize_fd` is the read end of the picker's SIGWINCH self-pipe (see
    `_pick_posix`); a byte there wins over a keypress and comes back as
    the synthetic "resize" action. Returning — rather than redrawing here —
    matters: the `finally` restores cooked mode first, so the caller never
    renders while raw mode (no OPOST) would staircase the output.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        # TCSADRAIN, not setraw's default TCSAFLUSH: a keypress that lands
        # between reads (e.g. racing a resize redraw) must survive re-entry,
        # not be flushed with the queue.
        tty.setraw(fd, termios.TCSADRAIN)
        ready = select.select([fd, resize_fd], [], [])[0]
        if resize_fd in ready:
            # Drain so a flurry of resizes coalesces into one redraw.
            os.read(resize_fd, 1024)
            return "resize"
        data = os.read(fd, 1)
        if data == b"\x1b":
            # Arrow keys arrive as ESC [ A / ESC O A; a bare Esc sends nothing
            # more, so a short poll distinguishes the two.
            while len(data) < 3 and select.select([fd], [], [], 0.02)[0]:
                data += os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return _decode_key(data)


def _picker_window(total: int, cursor: int, rows: int) -> tuple[int, int]:
    """Half-open [start, end) of row indices to show for this cursor.

    Rich's Live defaults to vertical_overflow="ellipsis", which keeps the
    *first* screenful of a taller-than-terminal render (LiveRender renders
    `lines[: height - 1]` plus an ellipsis line). So without windowing the
    bottom of a long list is never drawn and the cursor vanishes on the way
    down. We scroll the viewport to keep the cursor inside it, leaving a
    one-row margin at each edge when there is more list to reveal.

    This only holds if each row costs exactly one terminal line —
    `_picker_view` is responsible for that, by truncating rather than wrapping.
    """
    if rows <= 0 or total <= rows:
        return 0, total
    # Anchor the window on the "page" the cursor falls in, then nudge so the
    # cursor is never pinned to the very top/bottom edge while more rows exist.
    start = max(0, min(cursor - rows // 2, total - rows))
    return start, start + rows


def _picker_view(
    rows: Sequence[PickerRow],
    columns: Sequence[PickerColumn],
    selected: set[int],
    cursor: int,
    console: Console,
    hint: str,
) -> Group:
    # Chrome is an unconditional 5 lines: 2 for the table (header row + header
    # rule), 1 for the hint, and 2 for the scroll indicators — which are always
    # rendered, blank when there is nothing above/below, so the reserve holds at
    # the list ends too and the frame doesn't jitter by a row as you scroll past
    # them. The single hint line is why `hint` must not wrap.
    visible = max(1, console.size.height - 5)
    start, end = _picker_window(len(rows), cursor, visible)

    # `_picker_window` budgets in rows, so every row must cost exactly one
    # terminal line. `no_wrap`/`ellipsis` on every column is what buys that —
    # a wrapped row costs more than its one budgeted line and overflows.
    #
    # The ratios matter as much as the truncation. Left to itself, an
    # all-no_wrap table measures wider than the terminal (slugs and titles run
    # long), Rich falls through to its last-resort even reduction, and *every*
    # column shrinks — the marker and checkbox collapse to nothing. Declaring
    # the elastic columns flexible (`ratio` + `expand`) hands Rich the
    # slack it needs from them alone, so the fixed narrow columns survive down
    # to ~50 cells.
    table = Table(show_lines=False, show_edge=False, pad_edge=False, expand=True)
    table.add_column("", width=1, no_wrap=True, overflow="ellipsis")
    table.add_column("sel", width=3, no_wrap=True, overflow="ellipsis")
    for column in columns:
        table.add_column(
            column.header,
            width=column.width,
            ratio=column.ratio,
            no_wrap=True,
            overflow="ellipsis",
        )
    for index in range(start, end):
        table.add_row(
            Text("❯" if index == cursor else " "),
            # Text, not str: a bare "[x]" would be eaten as Rich markup.
            Text("[x]" if index in selected else "[ ]"),
            *rows[index].cells,
            style="reverse" if index == cursor else None,
        )
    # These sit outside the table and wrap on their own, so they need the same
    # truncation the columns got — a hint line alone can run past 60 cells.
    def _line(text: str) -> Text:
        return Text(text, style="dim", no_wrap=True, overflow="ellipsis")

    return Group(
        _line(f"  ↑ {start} more above" if start > 0 else ""),
        table,
        _line(f"  ↓ {len(rows) - end} more below" if end < len(rows) else ""),
        _line(hint),
    )


def _pick_posix(
    rows: Sequence[PickerRow],
    columns: Sequence[PickerColumn],
    selected: set[int],
    hint: str,
) -> list[str] | None:
    """The arrow-key loop. See `pick` for the contract."""
    console = Console()
    cursor = 0
    # SIGWINCH self-pipe: `_read_key` blocks in os.read/select, and PEP 475
    # retries reads around signals, so a flag set by a handler would never be
    # seen while the read stays blocked. The wakeup fd turns the signal into a
    # readable byte `_read_key` can select on. The no-op handler is required —
    # SIGWINCH is ignored by default, and only signals with a Python-level
    # handler reach the wakeup fd. Installed for the whole picker so a resize
    # landing between keypresses (cooked mode) is buffered, not lost.
    resize_read, resize_write = os.pipe()
    os.set_blocking(resize_write, False)
    previous_wakeup = signal.set_wakeup_fd(resize_write)
    previous_handler = signal.signal(signal.SIGWINCH, lambda signum, frame: None)
    try:
        with Live(
            _picker_view(rows, columns, selected, cursor, console, hint),
            console=console,
            auto_refresh=False,
            transient=True,
        ) as live:
            while True:
                key = _read_key(resize_read)
                if key == "cancel":
                    raise KeyboardInterrupt
                if key == "quit":
                    return None
                if key == "enter":
                    return [rows[i].key for i in sorted(selected)]
                if key == "up":
                    cursor = (cursor - 1) % len(rows)
                elif key == "down":
                    cursor = (cursor + 1) % len(rows)
                elif key == "space":
                    selected ^= {cursor}
                elif key == "all":
                    selected = set(range(len(rows)))
                elif key == "none":
                    selected = set()
                # "resize" needs no branch: falling through re-renders, and
                # _picker_view reads console.size fresh on every render.
                live.update(
                    _picker_view(rows, columns, selected, cursor, console, hint),
                    refresh=True,
                )
    finally:
        signal.signal(signal.SIGWINCH, previous_handler)
        signal.set_wakeup_fd(previous_wakeup)
        os.close(resize_read)
        os.close(resize_write)


def _pick_numbered(
    rows: Sequence[PickerRow],
    columns: Sequence[PickerColumn],
    selected: set[int],
) -> list[str] | None:
    """The non-POSIX input path: echo the rows numbered, read with `typer.prompt`.

    Reaches no `termios`, `tty`, `select`, `signal`, or `rich.Live` call, so it
    works where the arrow-key loop cannot even import. It needs no Ctrl-C
    handling of its own either: `typer.prompt` reads in cooked mode, so Ctrl-C
    raises `click.Abort` and aborts the command before this returns.

    The arrow-key hint does not apply here, so this path prints its own keys.
    """
    widths = [
        max(len(column.header), *(len(row.cells[i]) for row in rows))
        for i, column in enumerate(columns)
    ]
    while True:
        for number, row in enumerate(rows, start=1):
            marked = "[x]" if number - 1 in selected else "[ ]"
            cells = "  ".join(
                cell.ljust(width) for cell, width in zip(row.cells, widths)
            )
            typer.echo(f"  {number}. {marked} {cells}")
        answer = typer.prompt(
            "Toggle by number, `a` all, `n` none, ENTER to confirm, `q` to quit",
            default="",
            show_default=False,
        ).strip()
        if answer == "":
            return [rows[i].key for i in sorted(selected)]
        if answer == "q":
            return None
        if answer == "a":
            selected = set(range(len(rows)))
        elif answer == "n":
            selected = set()
        elif answer.isdigit() and 1 <= int(answer) <= len(rows):
            selected ^= {int(answer) - 1}
        else:
            typer.secho(f"Not a choice: {answer}", fg=typer.colors.YELLOW, err=True)


def pick(
    rows: Sequence[PickerRow],
    columns: Sequence[PickerColumn],
    *,
    checked: Collection[str] = (),
    hint: str,
) -> list[str] | None:
    """Multi-select `rows`; the confirmed keys, or None when the human quit.

    `checked` seeds the selection by key. `hint` is the footer line on the
    arrow-key path and must be a single line — `_picker_view` reserves exactly
    one row for it.

    An empty list and `None` are different answers: the first is "confirmed,
    nothing selected", the second is "backed out". Callers that must not act on
    a quit depend on telling them apart.

    Raises `KeyboardInterrupt` on Ctrl-C, on both paths, so a caller that would
    otherwise write files on a confirmed-empty answer can abort instead.
    """
    selected = {index for index, row in enumerate(rows) if row.key in checked}
    if os.name == "posix":
        return _pick_posix(rows, columns, selected, hint)
    return _pick_numbered(rows, columns, selected)
