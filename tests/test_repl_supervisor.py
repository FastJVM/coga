"""Tests for the PTY watcher that releases an interactive REPL on a
sentinel-file done signal."""

from __future__ import annotations

import os
import signal
import sys
import time

import pytest

from relay.repl_supervisor import (
    SENTINEL_ENV,
    _TIMEOUT_EXIT_CODE,
    _TTY_SANITIZE,
    _classify_exit,
    _sentinel_signals_done,
    ReplOutcome,
    emit_done_marker,
    run_with_done_marker,
)


def _signaled(sig: int) -> int:
    """A raw waitpid status for a child killed by `sig` (no core dump bit)."""
    return sig


def _exited(code: int) -> int:
    """A raw waitpid status for a child that exited with `code`."""
    return code << 8


def test_classify_exit_passthrough_when_not_signalled() -> None:
    """No watcher stop → the child's own status passes straight through."""
    assert _classify_exit(_exited(0), term_kind=None) == (0, "natural", [])
    assert _classify_exit(_exited(7), term_kind=None) == (7, "natural", [])
    assert _classify_exit(_signaled(signal.SIGSEGV), term_kind=None) == (
        128 + signal.SIGSEGV,
        "crash",
        [],
    )


def test_classify_exit_our_signal_is_clean_done() -> None:
    """Death from our own SIGTERM/SIGKILL after a done stop reports a clean 0."""
    code, kind, notes = _classify_exit(_signaled(signal.SIGTERM), term_kind="done")
    assert (code, kind) == (0, "done")
    assert any("exit 0" in n for n in notes)

    code, kind, _ = _classify_exit(_signaled(signal.SIGKILL), term_kind="done")
    assert (code, kind) == (0, "done")


def test_classify_exit_timeout_teardown_is_non_zero() -> None:
    """Death from our own signal after a *timeout* stop reports the timeout exit
    code and kind — a wedge must not masquerade as a clean done."""
    code, kind, notes = _classify_exit(
        _signaled(signal.SIGTERM), term_kind="timeout"
    )
    assert (code, kind) == (_TIMEOUT_EXIT_CODE, "timeout")
    assert any("timeout" in n for n in notes)

    # A child that self-exits after we sent the timeout SIGTERM is still a
    # timeout teardown, not a clean done.
    code, kind, _ = _classify_exit(_exited(0), term_kind="timeout")
    assert (code, kind) == (_TIMEOUT_EXIT_CODE, "timeout")


def test_classify_exit_surfaces_real_crash_after_stop() -> None:
    """A crash by a non-our signal during teardown is surfaced as a crash, not
    masked — regardless of whether we were tearing down for done or timeout."""
    code, kind, notes = _classify_exit(_signaled(signal.SIGSEGV), term_kind="done")
    assert (code, kind) == (128 + signal.SIGSEGV, "crash")
    assert any("real crash" in n for n in notes)

    code, kind, _ = _classify_exit(_signaled(signal.SIGSEGV), term_kind="timeout")
    assert (code, kind) == (128 + signal.SIGSEGV, "crash")


def test_no_tty_falls_back_to_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """No-TTY callers (pytest, CI) skip the PTY path and just shell out."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    outcome = run_with_done_marker(["true"], env={})
    assert (outcome.exit_code, outcome.kind) == (0, "natural")

    outcome = run_with_done_marker(["false"], env={})
    assert outcome.exit_code != 0


def _run_through_pty(
    monkeypatch: pytest.MonkeyPatch,
    cmd: list[str],
    *,
    session_id: str | None = None,
) -> ReplOutcome:
    """Force the PTY path with /dev/null fds for output and input."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    devnull_out = os.open(os.devnull, os.O_WRONLY)
    devnull_in = os.open(os.devnull, os.O_RDONLY)
    try:
        return run_with_done_marker(
            cmd,
            env={"PATH": os.environ.get("PATH", "")},
            session_id=session_id,
            output_fd=devnull_out,
            input_fd=devnull_in,
        )
    finally:
        os.close(devnull_out)
        os.close(devnull_in)


def test_natural_exit_passes_through_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child that exits on its own without signalling done → exit code is
    forwarded."""
    outcome = _run_through_pty(monkeypatch, ["bash", "-c", "exit 7"])
    assert (outcome.exit_code, outcome.kind) == (7, "natural")


def _run_through_pty_idle(
    monkeypatch: pytest.MonkeyPatch,
    cmd: list[str],
    *,
    idle_timeout: float | None = None,
    max_session: float | None = None,
) -> ReplOutcome:
    """Force the PTY path with a liveness backstop and /dev/null fds."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    devnull_out = os.open(os.devnull, os.O_WRONLY)
    devnull_in = os.open(os.devnull, os.O_RDONLY)
    try:
        return run_with_done_marker(
            cmd,
            env={"PATH": os.environ.get("PATH", "")},
            idle_timeout=idle_timeout,
            max_session=max_session,
            output_fd=devnull_out,
            input_fd=devnull_in,
        )
    finally:
        os.close(devnull_out)
        os.close(devnull_in)


def test_idle_timeout_terminates_silent_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A REPL that never signals done and goes silent is torn down by the
    idle-timeout backstop and reported as a *timeout* — non-zero exit, kind
    `timeout` — NOT a clean done.

    This is the stuck-agent case — an agent that stalls or crashes before
    reaching `relay bump` / `mark done` / `panic` — that would otherwise block
    a `relay recurring` sweep forever. Without the timeout the `sleep 30` here
    would hang the test; we assert it returns promptly instead. The non-zero
    classification is what lets the sweep record the wedge instead of pausing it
    as a deliberate human park.
    """
    start = time.monotonic()
    outcome = _run_through_pty_idle(
        monkeypatch, ["bash", "-c", "sleep 30"], idle_timeout=0.5
    )
    elapsed = time.monotonic() - start
    assert (outcome.exit_code, outcome.kind) == (_TIMEOUT_EXIT_CODE, "timeout")
    assert elapsed < 10  # torn down on idle, not after the full sleep


def test_idle_timeout_does_not_fire_on_self_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A child that exits within the idle window is left alone — the backstop
    must not pre-empt a REPL that finishes on its own, so its real exit code
    still passes through as a natural exit."""
    outcome = _run_through_pty_idle(
        monkeypatch, ["bash", "-c", "exit 7"], idle_timeout=30
    )
    assert (outcome.exit_code, outcome.kind) == (7, "natural")


def test_max_session_terminates_output_producing_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A REPL stuck in an *output-producing* loop never goes idle, so only the
    wall-clock max-session cap can catch it. With idle-timeout off and a short
    max-session, a child that streams forever is torn down as a timeout.

    This is the gap idle-timeout misses: the busy loop keeps the PTY active, so
    `last_activity` keeps refreshing and the idle backstop never fires."""
    start = time.monotonic()
    outcome = _run_through_pty_idle(
        monkeypatch,
        ["bash", "-c", "while true; do echo busy; sleep 0.05; done"],
        idle_timeout=None,
        max_session=0.5,
    )
    elapsed = time.monotonic() - start
    assert (outcome.exit_code, outcome.kind) == (_TIMEOUT_EXIT_CODE, "timeout")
    assert elapsed < 10  # torn down on the wall-clock cap, not left to spin


def test_sentinel_file_terminates_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child that writes $RELAY_DONE_SENTINEL → supervisor SIGTERMs it.

    This is the only done channel, and it survives TUI agents (Claude Code,
    Codex) which capture bash subprocess stdout into a private pipe rather
    than echoing it to the PTY: the supervisor reads the file regardless of
    where the child's stdout goes.
    """
    outcome = _run_through_pty(
        monkeypatch,
        ["bash", "-c", f'printf done > "${SENTINEL_ENV}"; sleep 30'],
    )
    assert (outcome.exit_code, outcome.kind) == (0, "done")


def test_session_id_match_terminates_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sentinel content naming *this* session → supervisor SIGTERMs it."""
    outcome = _run_through_pty(
        monkeypatch,
        ["bash", "-c", f'printf "/repo/tasks/mine" > "${SENTINEL_ENV}"; sleep 30'],
        session_id="/repo/tasks/mine",
    )
    assert (outcome.exit_code, outcome.kind) == (0, "done")


def test_session_id_mismatch_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sentinel content naming a *different* ticket → no teardown.

    This is the leak that killed sessions: a nested `relay bump`/`mark done`
    (e.g. a test fixture in a tempdir) inherited `RELAY_DONE_SENTINEL` and
    wrote it. With session scoping the supervisor ignores the stray write and
    the child runs to its own exit — here exit 5, proving we did NOT SIGTERM.
    """
    outcome = _run_through_pty(
        monkeypatch,
        ["bash", "-c", f'printf "/tmp/fixture/other" > "${SENTINEL_ENV}"; exit 5'],
        session_id="/repo/tasks/mine",
    )
    assert (outcome.exit_code, outcome.kind) == (5, "natural")


def _run_through_pty_capture(
    monkeypatch: pytest.MonkeyPatch,
    cmd: list[str],
    *,
    session_id: str | None = None,
) -> tuple[ReplOutcome, bytes]:
    """Force the PTY path with a pipe for output so we can inspect what the
    watcher wrote to the terminal. Returns (outcome, captured_output)."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    read_fd, write_fd = os.pipe()
    devnull_in = os.open(os.devnull, os.O_RDONLY)
    try:
        outcome = run_with_done_marker(
            cmd,
            env={"PATH": os.environ.get("PATH", "")},
            session_id=session_id,
            output_fd=write_fd,
            input_fd=devnull_in,
        )
    finally:
        os.close(write_fd)  # EOF-bound the read below
        captured = os.read(read_fd, 1 << 16)
        os.close(read_fd)
        os.close(devnull_in)
    return outcome, captured


def test_tty_sanitize_emitted_after_signal_teardown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A signal-killed TUI never restores its own terminal modes, so the
    watcher must emit the sanitizing reset itself — otherwise the keyboard is
    left "dead" (alt-screen / mouse / bracketed-paste still on) and the session
    reads as hung even though the bump already succeeded."""
    outcome, out = _run_through_pty_capture(
        monkeypatch,
        ["bash", "-c", f'printf "/repo/tasks/mine" > "${SENTINEL_ENV}"; sleep 30'],
        session_id="/repo/tasks/mine",
    )
    assert outcome.exit_code == 0
    assert _TTY_SANITIZE in out


def test_tty_sanitize_clears_keyboard_protocols() -> None:
    """A leftover keyboard-input protocol turns every keypress into an escape
    report (e.g. `\x1b[5;1:3u`), so the sanitize payload must disable the kitty
    keyboard protocol and xterm modifyOtherKeys, not just the DEC private
    modes. Regression guard for the wedged-keyboard-after-bump bug."""
    assert b"\x1b[<u" in _TTY_SANITIZE  # kitty protocol: pop stack
    assert b"\x1b[=0;1u" in _TTY_SANITIZE  # kitty protocol: clear flags
    assert b"\x1b[>4;0m" in _TTY_SANITIZE  # xterm modifyOtherKeys off


def test_tty_sanitize_skipped_on_self_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A child that exits on its own runs its own terminal cleanup, so the
    watcher must NOT inject the reset — doing so would clobber the modes a
    still-running parent UI legitimately set."""
    outcome, out = _run_through_pty_capture(monkeypatch, ["bash", "-c", "exit 0"])
    assert outcome.exit_code == 0
    assert _TTY_SANITIZE not in out


def test_emit_done_marker_writes_session_id_content(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`emit_done_marker(session_id=...)` writes the id as the file content."""
    sentinel = tmp_path / "done"
    monkeypatch.setenv(SENTINEL_ENV, str(sentinel))
    emit_done_marker(session_id="/repo/tasks/mine")
    assert sentinel.read_text().strip() == "/repo/tasks/mine"


def test_emit_done_marker_writes_sentinel(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`emit_done_marker` writes the sentinel file when env var is set, and
    prints nothing — the file is the only channel, and any in-band print
    would leak into a TUI's visible output / a parent supervisor's PTY."""
    sentinel = tmp_path / "done"
    monkeypatch.setenv(SENTINEL_ENV, str(sentinel))
    emit_done_marker()
    assert sentinel.exists()
    assert capsys.readouterr().out == ""


def test_emit_done_marker_write_failure_is_silent(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The sentinel file is the only channel: if its write raises there is
    nothing to fall back to, so the call swallows the error and prints
    nothing rather than emitting an in-band signal."""
    # Parent directory does not exist → the atomic write's `mkstemp` raises.
    sentinel = tmp_path / "missing-dir" / "done"
    monkeypatch.setenv(SENTINEL_ENV, str(sentinel))
    emit_done_marker()  # must not raise
    assert not sentinel.exists()
    assert capsys.readouterr().out == ""


def test_bare_touch_ignores_empty_sentinel(tmp_path) -> None:
    """Hardened legacy path: a zero-byte sentinel (a partial write) must NOT
    read as done, even without a session_id — that was the teardown footgun."""
    sentinel = tmp_path / "done"
    sentinel.write_text("")
    assert _sentinel_signals_done(str(sentinel), None) is False


def test_bare_touch_accepts_nonempty_sentinel(tmp_path) -> None:
    """Legacy contract preserved: any non-empty content ends the session when
    no session_id scopes the channel."""
    sentinel = tmp_path / "done"
    sentinel.write_text("done\n")
    assert _sentinel_signals_done(str(sentinel), None) is True


def test_sentinel_missing_is_not_done(tmp_path) -> None:
    assert _sentinel_signals_done(str(tmp_path / "absent"), None) is False
    assert _sentinel_signals_done(str(tmp_path / "absent"), "/repo/x") is False


def test_emit_done_marker_no_env_is_silent(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without the env var (non-supervised terminal), there is no sentinel to
    write and no in-band channel, so emit nothing — a print would only leak an
    internal teardown string into the human's visible transcript."""
    monkeypatch.delenv(SENTINEL_ENV, raising=False)
    emit_done_marker()
    assert capsys.readouterr().out == ""
