from __future__ import annotations

import pytest

from conftest import windows_interactive_skip

from coga.picker import PickerColumn, PickerRow, pick


COLUMNS = (PickerColumn("name", ratio=1),)


def _rows(*keys: str) -> list[PickerRow]:
    return [PickerRow(key=key, cells=(key,)) for key in keys]


def _feed_keys(monkeypatch: pytest.MonkeyPatch, keys: list[str]) -> None:
    """Drive the picker with decoded key actions instead of a raw terminal."""
    pending = iter(keys)
    monkeypatch.setattr("coga.picker._read_key", lambda _resize_fd: next(pending))


def _feed_prompts(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    """Drive the numbered path by answering its `typer.prompt` calls in order."""
    pending = iter(answers)
    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: next(pending))


def test_decode_key() -> None:
    from coga.picker import _decode_key

    assert _decode_key(b"\x1b[A") == "up"
    assert _decode_key(b"k") == "up"
    assert _decode_key(b"\x1b[B") == "down"
    assert _decode_key(b"j") == "down"
    assert _decode_key(b" ") == "space"
    assert _decode_key(b"\r") == "enter"
    assert _decode_key(b"\n") == "enter"
    assert _decode_key(b"q") == "quit"
    assert _decode_key(b"\x1b") == "quit"  # bare Esc
    # Ctrl-C is its own action, not a synonym for `q`: `tty.setraw` clears ISIG
    # so it arrives as a byte, and a caller that writes files on a confirmed
    # answer has to be able to tell "abort" from "back out".
    assert _decode_key(b"\x03") == "cancel"
    assert _decode_key(b"a") == "all"
    assert _decode_key(b"n") == "none"
    assert _decode_key(b"x") == ""  # unknown keys are ignored


def test_picker_window_keeps_cursor_visible() -> None:
    """Long lists window to a viewport that always contains the cursor."""
    from coga.picker import _picker_window

    # Short list: no windowing, everything is shown.
    assert _picker_window(total=5, cursor=0, rows=10) == (0, 5)
    assert _picker_window(total=10, cursor=9, rows=10) == (0, 10)

    # Long list: the window is exactly `rows` tall and never drops the cursor.
    for cursor in range(50):
        start, end = _picker_window(total=50, cursor=cursor, rows=10)
        assert end - start == 10
        assert start <= cursor < end
        assert 0 <= start and end <= 50

    # Top and bottom clamp so we never scroll past the ends.
    assert _picker_window(total=50, cursor=0, rows=10)[0] == 0
    assert _picker_window(total=50, cursor=49, rows=10) == (40, 50)

    # A degenerate terminal height still yields a usable window.
    assert _picker_window(total=50, cursor=20, rows=0) == (0, 50)


def test_picker_view_fits_the_terminal_at_every_size() -> None:
    """The rendered picker is exactly one line per row plus 5 of chrome.

    `_picker_window` budgets in rows while the terminal budgets in lines,
    so anything that wraps — a row, the hint line, a scroll indicator — costs
    more than its one budgeted line. Live keeps only the *first* screenful of
    an overflowing render, so the cursor disappears on the way down the list.
    """
    from rich.console import Console

    from coga.picker import _picker_view

    columns = (
        PickerColumn("slug", ratio=2),
        PickerColumn("status"),
        PickerColumn("owner", ratio=1),
        PickerColumn("step", ratio=1),
        PickerColumn("title", ratio=3),
    )
    hint = "↑/↓ move · Space toggle · a all · n none · Enter launch · q quit"

    def row(
        index: int,
        title: str,
        owner: str = "zach",
        step: str = "1 (implement)",
    ) -> PickerRow:
        # Slugs are derived from titles, so real ones run this long. A short
        # stand-in leaves the table inside its width budget and the layout
        # never gets stressed.
        slug = f"a-command-that-reads-machine-local-config-gives-a-{index:02d}"
        return PickerRow(
            key=slug, cells=(slug, "in_progress", owner, step, title)
        )

    rows = [
        row(
            index,
            f"candidate {index} with a deliberately long title that wraps on "
            "any terminal narrower than a billboard",
        )
        for index in range(39)
    ]
    # Long values in narrow columns push the table over budget, which is what
    # makes Rich shrink every column and wrap the "[x]" checkbox. This step is
    # an existing valid workflow label, not a synthetic extreme.
    rows[7] = row(
        7,
        "short",
        owner="replace-with-human-name",
        step="2 (human-owns-and-finishes)",
    )
    # Mid-list cursors matter: only there are both scroll indicators drawn, so
    # only there does an under-reserved chrome budget overflow.
    cursors = [0, 1, len(rows) // 2, len(rows) - 2, len(rows) - 1]

    for width, height in [(100, 50), (80, 24), (50, 30), (40, 30), (100, 5)]:
        # `max(1, ...)` is the floor for degenerate terminals: a 5-line
        # terminal still needs one row plus 5 lines of chrome.
        visible = max(1, height - 5)
        expected = min(len(rows), visible) + 5
        for cursor in cursors:
            console = Console(width=width, height=height)
            # No explicit `height` render option: Rich would pad or crop to it
            # and the assertion would pass vacuously.
            lines = console.render_lines(
                _picker_view(rows, columns, {cursor}, cursor, console, hint)
            )
            # Exact, not `<=`: a wrapped row can still happen to fit the
            # terminal while breaking the one-line-per-row invariant.
            # Both scroll-indicator slots are always rendered, blank when there
            # is nothing above or below, so chrome is an unconditional 5 lines
            # and the frame does not jitter by a row at either end of the list.
            assert len(lines) == expected, (
                f"{width}x{height} cursor={cursor} rendered {len(lines)} lines, "
                f"expected {expected}"
            )
            # Fitting is only half of it: the cursor's row has to be one of the
            # rows actually drawn. It carries the reverse style, which — unlike
            # the "❯" marker column — survives however narrow the terminal.
            highlighted = sum(
                any(segment.style and segment.style.reverse for segment in line)
                for line in lines
            )
            assert highlighted == 1, (
                f"cursor row not drawn at {width}x{height} cursor={cursor}"
            )
            # Truncation alone fits the terminal but can still gut the layout:
            # if Rich has to shrink every column it empties the one-cell marker
            # and three-cell checkbox first, and the picker stops showing where
            # the cursor is or what is selected. 50 cells is the narrowest
            # width these survive; below that all seven columns cannot fit.
            if width >= 50:
                rendered = [
                    "".join(segment.text for segment in line) for line in lines
                ]
                assert any("❯" in text for text in rendered), (
                    f"cursor marker collapsed at {width}x{height} cursor={cursor}"
                )
                assert any("[x]" in text for text in rendered), (
                    f"checkbox collapsed at {width}x{height} cursor={cursor}"
                )


@windows_interactive_skip
def test_read_key_resize_beats_pending_keypress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A byte on the resize pipe wins over a queued keypress and comes back as
    the synthetic "resize" action; the keypress survives for the next read."""
    import os
    import pty
    import tty
    import types

    from coga.picker import _read_key

    master, slave = pty.openpty()
    resize_read, resize_write = os.pipe()
    monkeypatch.setattr("sys.stdin", types.SimpleNamespace(fileno=lambda: slave))
    try:
        # Raw before writing: a byte queued while the slave is still canonical
        # sits in the line buffer and never becomes select()-readable.
        tty.setraw(slave)
        os.write(master, b"j")
        # What signal.set_wakeup_fd would deliver for SIGWINCH.
        os.write(resize_write, b"\x1c")
        assert _read_key(resize_read) == "resize"
        assert _read_key(resize_read) == "down"
    finally:
        for fd in (master, slave, resize_read, resize_write):
            os.close(fd)


@windows_interactive_skip
def test_pick_seeds_the_selection_from_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`checked` pre-checks by key, so confirming takes one ENTER."""
    _feed_keys(monkeypatch, ["enter"])

    assert pick(
        _rows("claude", "codex"), COLUMNS, checked=("claude",), hint="h"
    ) == ["claude"]


@windows_interactive_skip
def test_pick_toggles_and_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    """Space toggles the row under the cursor; the result keeps row order."""
    _feed_keys(monkeypatch, ["space", "down", "space", "enter"])

    assert pick(_rows("claude", "codex"), COLUMNS, hint="h") == [
        "claude",
        "codex",
    ]


@windows_interactive_skip
def test_pick_all_and_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """`a` checks everything, `n` clears it — including the pre-checked seed."""
    _feed_keys(monkeypatch, ["all", "enter"])
    assert pick(_rows("claude", "codex"), COLUMNS, hint="h") == [
        "claude",
        "codex",
    ]

    _feed_keys(monkeypatch, ["none", "enter"])
    assert (
        pick(_rows("claude", "codex"), COLUMNS, checked=("claude",), hint="h")
        == []
    )


@windows_interactive_skip
def test_pick_distinguishes_quit_from_confirmed_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`q` returns None; confirming with nothing checked returns [].

    A caller that writes files on a confirmed answer has to tell these apart —
    `coga init` keeps the packaged config on the first and rewrites it on the
    second.
    """
    _feed_keys(monkeypatch, ["quit"])
    assert pick(_rows("claude", "codex"), COLUMNS, checked=("claude",), hint="h") is None

    _feed_keys(monkeypatch, ["none", "enter"])
    assert pick(_rows("claude", "codex"), COLUMNS, checked=("claude",), hint="h") == []


@windows_interactive_skip
def test_pick_raises_keyboard_interrupt_on_ctrl_c(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ctrl-C aborts rather than reading as `q`.

    Raw mode clears ISIG, so the terminal never raises this itself; `pick` is
    what turns the byte back into the interrupt cooked mode would have sent.
    """
    _feed_keys(monkeypatch, ["cancel"])

    with pytest.raises(KeyboardInterrupt):
        pick(_rows("claude", "codex"), COLUMNS, checked=("claude",), hint="h")


def test_pick_numbered_toggles_by_number(monkeypatch: pytest.MonkeyPatch) -> None:
    """The non-POSIX path toggles by number and confirms on a bare ENTER."""
    _feed_prompts(monkeypatch, ["2", ""])

    from coga.picker import _pick_numbered

    assert _pick_numbered(_rows("claude", "codex"), COLUMNS, {0}) == [
        "claude",
        "codex",
    ]


def test_pick_numbered_all_none_and_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    """`a`/`n` select all and none; `q` backs out with None."""
    from coga.picker import _pick_numbered

    _feed_prompts(monkeypatch, ["a", ""])
    assert _pick_numbered(_rows("claude", "codex"), COLUMNS, set()) == [
        "claude",
        "codex",
    ]

    _feed_prompts(monkeypatch, ["n", ""])
    assert _pick_numbered(_rows("claude", "codex"), COLUMNS, {0, 1}) == []

    _feed_prompts(monkeypatch, ["q"])
    assert _pick_numbered(_rows("claude", "codex"), COLUMNS, {0}) is None


def test_pick_numbered_reprompts_on_garbage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unparseable input re-opens the prompt instead of confirming."""
    from coga.picker import _pick_numbered

    # "9" is out of range and "zzz" is not a command: both must re-prompt
    # rather than fall through to a confirm.
    _feed_prompts(monkeypatch, ["9", "zzz", "1", ""])

    assert _pick_numbered(_rows("claude", "codex"), COLUMNS, set()) == ["claude"]
    assert "Not a choice" in capsys.readouterr().err


def test_pick_dispatches_to_the_numbered_path_off_posix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`pick` chooses its input path at call time, so Windows never reaches
    `termios`. Dispatching at import time would make this untestable here."""
    monkeypatch.setattr("coga.picker.os.name", "nt")
    _feed_prompts(monkeypatch, [""])

    assert pick(
        _rows("claude", "codex"), COLUMNS, checked=("codex",), hint="h"
    ) == ["codex"]
