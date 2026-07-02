"""Tests for the headless (`autonomy: auto`) agent runner: captured, teed
output; closed stdin; and the idle / max-session liveness limits."""

from __future__ import annotations

import os
import time
from pathlib import Path

from coga.headless import run_headless
from coga.repl_supervisor import _TIMEOUT_EXIT_CODE


def _run(tmp_path: Path, script: str, **kwargs):
    """Run a small shell script headless, returning (outcome, capture, live).

    `live` is what streamed to the caller-facing fd — captured through a
    temp file standing in for stdout, the same trick the PTY watcher tests
    use — and `capture` is the durable tee file's content.
    """
    capture_path = tmp_path / "auto-run.log"
    live_path = tmp_path / "live-stream.out"
    with open(live_path, "wb") as live:
        outcome = run_headless(
            ["sh", "-c", script],
            {"PATH": os.environ["PATH"]},
            capture_path=capture_path,
            output_fd=live.fileno(),
            **kwargs,
        )
    return outcome, capture_path.read_text(), live_path.read_text()


def test_headless_tees_stdout_and_stderr_to_capture_and_stream(
    tmp_path: Path,
) -> None:
    """Both streams land in the capture file AND the live stream fd."""
    outcome, capture, live = _run(tmp_path, "echo out; echo err 1>&2")
    assert (outcome.exit_code, outcome.kind) == (0, "natural")
    assert "out" in capture and "err" in capture
    assert "out" in live and "err" in live


def test_headless_passes_child_exit_code_through(tmp_path: Path) -> None:
    outcome, _, _ = _run(tmp_path, "exit 7")
    assert (outcome.exit_code, outcome.kind) == (7, "natural")


def test_headless_closes_stdin_so_input_needing_work_fails_fast(
    tmp_path: Path,
) -> None:
    """A child that reads stdin gets immediate EOF instead of hanging.

    `cat` with an open terminal stdin would block forever; under the runner
    it must drain /dev/null instantly and let the script finish.
    """
    start = time.monotonic()
    outcome, capture, _ = _run(tmp_path, "cat; echo after-stdin")
    assert time.monotonic() - start < 5.0
    assert (outcome.exit_code, outcome.kind) == (0, "natural")
    assert "after-stdin" in capture


def test_headless_idle_timeout_tears_down_silent_child(tmp_path: Path) -> None:
    """No output past the idle limit → SIGTERM teardown, timeout outcome."""
    start = time.monotonic()
    outcome, capture, _ = _run(tmp_path, "sleep 30", idle_timeout=0.5)
    assert time.monotonic() - start < 10.0
    assert (outcome.exit_code, outcome.kind) == (_TIMEOUT_EXIT_CODE, "timeout")
    # The capture file explains the 124 by itself.
    assert "idle-timeout" in capture


def test_headless_max_session_caps_a_child_still_producing_output(
    tmp_path: Path,
) -> None:
    """Wall-clock cap fires even while output keeps flowing (the case idle
    timeout misses)."""
    start = time.monotonic()
    outcome, capture, _ = _run(
        tmp_path,
        "while true; do echo tick; sleep 0.1; done",
        max_session=0.7,
    )
    assert time.monotonic() - start < 10.0
    assert (outcome.exit_code, outcome.kind) == (_TIMEOUT_EXIT_CODE, "timeout")
    assert "max-session" in capture
    assert "tick" in capture  # output up to the cap was still captured


def test_headless_overwrites_previous_capture(tmp_path: Path) -> None:
    """Each run replaces the file — the log keeps history; the file is the
    latest run's transcript."""
    capture_path = tmp_path / "auto-run.log"
    capture_path.write_text("stale previous run\n")
    with open(tmp_path / "live", "wb") as live:
        run_headless(
            ["sh", "-c", "echo fresh"],
            {"PATH": os.environ["PATH"]},
            capture_path=capture_path,
            output_fd=live.fileno(),
        )
    text = capture_path.read_text()
    assert "fresh" in text
    assert "stale previous run" not in text
