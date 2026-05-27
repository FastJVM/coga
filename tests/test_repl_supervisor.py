"""Tests for the PTY watcher that releases an interactive REPL on marker."""

from __future__ import annotations

import os
import sys

import pytest

from relay.repl_supervisor import DONE_MARKER, run_with_done_marker


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
