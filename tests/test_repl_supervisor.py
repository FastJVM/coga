"""Tests for the PTY watcher that releases an interactive REPL on marker."""

from __future__ import annotations

import os
import signal
import sys

import pytest

from relay.repl_supervisor import (
    DONE_MARKER,
    SENTINEL_ENV,
    _classify_exit,
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


def _run_through_pty(monkeypatch: pytest.MonkeyPatch, cmd: list[str]) -> int:
    """Force the PTY path with /dev/null fds for output and input."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    devnull_out = os.open(os.devnull, os.O_WRONLY)
    devnull_in = os.open(os.devnull, os.O_RDONLY)
    try:
        return run_with_done_marker(
            cmd,
            env={"PATH": os.environ.get("PATH", "")},
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
    """Child that touches $RELAY_DONE_SENTINEL → supervisor SIGTERMs it.

    This is the channel that survives TUI agents (Claude Code, Codex) which
    capture bash subprocess stdout into a private pipe rather than echoing it
    to the PTY — the marker bytes never reach the watcher in that case, but
    the file does.
    """
    code = _run_through_pty(
        monkeypatch,
        ["bash", "-c", f'touch "${SENTINEL_ENV}"; sleep 30'],
    )
    assert code == 0


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


def test_emit_done_marker_no_env_is_harmless(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without the env var (non-supervised terminal), only prints the marker."""
    monkeypatch.delenv(SENTINEL_ENV, raising=False)
    emit_done_marker()
    assert DONE_MARKER.decode() in capsys.readouterr().out
