"""Tests for the PTY watcher that releases an interactive REPL on marker."""

from __future__ import annotations

import os
import signal
import sys

import pytest

from relay.repl_supervisor import (
    DONE_MARKER,
    SENTINEL_ENV,
    _TTY_SANITIZE,
    _classify_exit,
    _sentinel_signals_done,
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
    assert _classify_exit(_exited(0), sent_term=False) == (0, [])
    assert _classify_exit(_exited(7), sent_term=False) == (7, [])
    assert _classify_exit(_signaled(signal.SIGSEGV), sent_term=False) == (
        128 + signal.SIGSEGV,
        [],
    )


def test_classify_exit_our_signal_is_clean_done() -> None:
    """Death from our own SIGTERM/SIGKILL after a stop reports a clean 0."""
    code, notes = _classify_exit(_signaled(signal.SIGTERM), sent_term=True)
    assert code == 0
    assert any("exit 0" in n for n in notes)

    code, _ = _classify_exit(_signaled(signal.SIGKILL), sent_term=True)
    assert code == 0


def test_classify_exit_surfaces_real_crash_after_stop() -> None:
    """A crash by a non-our signal during teardown is surfaced, not masked."""
    code, notes = _classify_exit(_signaled(signal.SIGSEGV), sent_term=True)
    assert code == 128 + signal.SIGSEGV
    assert any("real crash" in n for n in notes)


def test_no_tty_falls_back_to_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """No-TTY callers (pytest, CI) skip the PTY path and just shell out."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    code = run_with_done_marker(["true"], env={})
    assert code == 0

    code = run_with_done_marker(["false"], env={})
    assert code != 0


def _run_through_pty(
    monkeypatch: pytest.MonkeyPatch,
    cmd: list[str],
    *,
    session_id: str | None = None,
) -> int:
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


def test_marker_in_child_output_terminates_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child writes the marker → supervisor SIGTERMs it and reports 0.

    Without the watcher, the trailing `sleep 30` would block the test for
    half a minute; we assert it returns quickly with a clean exit code.
    """
    marker = DONE_MARKER.decode()
    code = _run_through_pty(
        monkeypatch, ["bash", "-c", f"echo '{marker}'; sleep 30"]
    )
    assert code == 0


def test_natural_exit_passes_through_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child that exits on its own without the marker → exit code is forwarded."""
    code = _run_through_pty(monkeypatch, ["bash", "-c", "exit 7"])
    assert code == 7


def test_sentinel_file_terminates_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child that writes $RELAY_DONE_SENTINEL → supervisor SIGTERMs it.

    This is the channel that survives TUI agents (Claude Code, Codex) which
    capture bash subprocess stdout into a private pipe rather than echoing it
    to the PTY — the marker bytes never reach the watcher in that case, but
    the file does.
    """
    code = _run_through_pty(
        monkeypatch,
        ["bash", "-c", f'printf done > "${SENTINEL_ENV}"; sleep 30'],
    )
    assert code == 0


def test_session_id_match_terminates_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sentinel content naming *this* session → supervisor SIGTERMs it."""
    code = _run_through_pty(
        monkeypatch,
        ["bash", "-c", f'printf "/repo/tasks/mine" > "${SENTINEL_ENV}"; sleep 30'],
        session_id="/repo/tasks/mine",
    )
    assert code == 0


def test_session_id_mismatch_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sentinel content naming a *different* ticket → no teardown.

    This is the leak that killed sessions: a nested `relay bump`/`mark done`
    (e.g. a test fixture in a tempdir) inherited `RELAY_DONE_SENTINEL` and
    wrote it. With session scoping the supervisor ignores the stray write and
    the child runs to its own exit — here exit 5, proving we did NOT SIGTERM.
    """
    code = _run_through_pty(
        monkeypatch,
        ["bash", "-c", f'printf "/tmp/fixture/other" > "${SENTINEL_ENV}"; exit 5'],
        session_id="/repo/tasks/mine",
    )
    assert code == 5


def _run_through_pty_capture(
    monkeypatch: pytest.MonkeyPatch,
    cmd: list[str],
    *,
    session_id: str | None = None,
) -> tuple[int, bytes]:
    """Force the PTY path with a pipe for output so we can inspect what the
    watcher wrote to the terminal. Returns (exit_code, captured_output)."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    read_fd, write_fd = os.pipe()
    devnull_in = os.open(os.devnull, os.O_RDONLY)
    try:
        code = run_with_done_marker(
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
    return code, captured


def test_tty_sanitize_emitted_after_signal_teardown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A signal-killed TUI never restores its own terminal modes, so the
    watcher must emit the sanitizing reset itself — otherwise the keyboard is
    left "dead" (alt-screen / mouse / bracketed-paste still on) and the session
    reads as hung even though the bump already succeeded."""
    code, out = _run_through_pty_capture(
        monkeypatch,
        ["bash", "-c", f'printf "/repo/tasks/mine" > "${SENTINEL_ENV}"; sleep 30'],
        session_id="/repo/tasks/mine",
    )
    assert code == 0
    assert _TTY_SANITIZE in out


def test_tty_sanitize_skipped_on_self_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A child that exits on its own runs its own terminal cleanup, so the
    watcher must NOT inject the reset — doing so would clobber the modes a
    still-running parent UI legitimately set."""
    code, out = _run_through_pty_capture(monkeypatch, ["bash", "-c", "exit 0"])
    assert code == 0
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
    """`emit_done_marker` writes the sentinel file when env var is set."""
    sentinel = tmp_path / "done"
    monkeypatch.setenv(SENTINEL_ENV, str(sentinel))
    emit_done_marker()
    assert sentinel.exists()
    # Fallback PTY marker still printed.
    assert DONE_MARKER.decode() in capsys.readouterr().out


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


def test_emit_done_marker_no_env_is_harmless(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without the env var (non-supervised terminal), only prints the marker."""
    monkeypatch.delenv(SENTINEL_ENV, raising=False)
    emit_done_marker()
    assert DONE_MARKER.decode() in capsys.readouterr().out
