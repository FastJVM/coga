"""Run a headless (`autonomy: auto`) agent CLI with captured, teed output.

`claude -p` and `codex exec` buffer most of their output until completion, so
an unattended run has no live console to watch. This runner makes such a run
observable after the fact instead: the child's combined stdout/stderr is
streamed through to the launcher's stdout (so a cron log still sees it) *and*
teed into a capture file next to the task, which the caller records in the
repo-global log along with the exit code.

stdin is redirected from `/dev/null`. Both configured CLIs receive their
prompt as an argv token (see `build_agent_command`), and both treat stdin as
*optional extra* input: `codex exec` appends piped stdin as a `<stdin>` block
and `claude -p` accepts piped context alongside `-p`. `/dev/null` yields
immediate EOF, so a run that would otherwise sit waiting for interactive
input fails fast instead of hanging the sweep.

Liveness mirrors the interactive PTY watcher (`repl_supervisor`): an optional
`idle_timeout` fires when the pipe produces no output for that long, and an
optional `max_session` caps wall-clock even while output still flows. Either
tears the child down (SIGTERM, then SIGKILL after the same grace period) and
reports the shared `_TIMEOUT_EXIT_CODE` with kind `"timeout"`, so callers
branch identically for both run styles.
"""

from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

from coga.repl_supervisor import _KILL_GRACE_SECONDS, _TIMEOUT_EXIT_CODE, ReplOutcome

# How often the read loop wakes when the pipe is quiet, bounding how late a
# liveness limit can fire. Matches the PTY watcher's sentinel poll cadence.
_POLL_INTERVAL = 0.25


def run_headless(
    cmd: list[str],
    env: Mapping[str, str],
    *,
    capture_path: Path,
    idle_timeout: float | None = None,
    max_session: float | None = None,
    cwd: "os.PathLike[str] | str | None" = None,
    output_fd: int | None = None,
) -> ReplOutcome:
    """Spawn `cmd` headless: stdin closed, stdout+stderr teed to `capture_path`.

    Returns a `ReplOutcome` — `natural` with the child's own exit code, or
    `timeout` (exit `_TIMEOUT_EXIT_CODE`) when a liveness limit tore it down.
    There is no `done` kind here: headless CLIs exit on their own when the
    run completes, so the sentinel-file channel never applies.

    `output_fd` exists for tests; production callers leave it None and the
    live stream goes to the real stdout.
    """
    out_fd = output_fd if output_fd is not None else sys.stdout.fileno()
    capture_path.parent.mkdir(parents=True, exist_ok=True)

    with open(capture_path, "wb") as capture:
        with subprocess.Popen(
            cmd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            # Own process group, like the PTY watcher's `pty.fork` session: a
            # liveness teardown must also reach any foreground tool the agent
            # spawned, or SIGTERM to the CLI queues behind it.
            start_new_session=True,
        ) as proc:
            try:
                outcome = _proxy_until_exit(
                    proc,
                    capture=capture,
                    out_fd=out_fd,
                    idle_timeout=idle_timeout,
                    max_session=max_session,
                )
            except BaseException:
                _terminate_process_group_on_abort(
                    proc,
                    capture=capture,
                    out_fd=out_fd,
                )
                raise
    return outcome


def _proxy_until_exit(
    proc: subprocess.Popen,
    *,
    capture,
    out_fd: int,
    idle_timeout: float | None,
    max_session: float | None,
) -> ReplOutcome:
    assert proc.stdout is not None
    pipe_fd = proc.stdout.fileno()

    def _note(line: str) -> None:
        _write_note(capture, out_fd, line)

    session_start = time.monotonic()
    last_activity = session_start
    term_kind: str | None = None
    term_deadline: float | None = None
    sent_kill = False

    def _trigger_term(reason: str) -> None:
        nonlocal term_kind, term_deadline
        term_kind = "timeout"
        term_deadline = time.monotonic() + _KILL_GRACE_SECONDS
        _note(f"stopping headless run — trigger={reason}")
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    while True:
        if term_kind is not None and not sent_kill:
            timeout = max(0.0, (term_deadline or 0) - time.monotonic())
        else:
            timeout = _POLL_INTERVAL
        try:
            rlist, _, _ = select.select([pipe_fd], [], [], timeout)
        except InterruptedError:
            continue

        now = time.monotonic()
        if term_kind is not None and not sent_kill and now >= (term_deadline or 0):
            sent_kill = True
            _note(
                f"child still alive after {_KILL_GRACE_SECONDS}s — "
                "escalating to SIGKILL"
            )
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        if (
            idle_timeout is not None
            and term_kind is None
            and now - last_activity >= idle_timeout
        ):
            _trigger_term(f"idle-timeout (no output for {idle_timeout:.0f}s)")

        if (
            max_session is not None
            and term_kind is None
            and now - session_start >= max_session
        ):
            _trigger_term(f"max-session (wall-clock exceeded {max_session:.0f}s)")

        if pipe_fd in rlist:
            try:
                chunk = os.read(pipe_fd, 4096)
            except OSError:
                chunk = b""
            if not chunk:
                break  # EOF — child closed stdout (exiting or killed)
            last_activity = time.monotonic()
            capture.write(chunk)
            capture.flush()
            try:
                os.write(out_fd, chunk)
            except OSError:
                pass

    code = proc.wait()
    if term_kind == "timeout":
        _note(
            f"reporting exit {_TIMEOUT_EXIT_CODE} "
            "(timeout — liveness limit, run never completed)"
        )
        return ReplOutcome(_TIMEOUT_EXIT_CODE, "timeout")
    if code < 0:
        # Killed by a signal we did not send — surface the conventional
        # `128 + signal` code rather than Popen's negative form.
        return ReplOutcome(128 - code, "crash")
    return ReplOutcome(code, "natural")


def _terminate_process_group_on_abort(
    proc: subprocess.Popen, *, capture, out_fd: int
) -> None:
    """Stop the headless child when the parent is interrupted mid-run."""
    if proc.poll() is not None:
        return
    _write_note(capture, out_fd, "aborting headless run — terminating process group")
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        proc.wait(timeout=_KILL_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass

    _write_note(
        capture,
        out_fd,
        f"child still alive after {_KILL_GRACE_SECONDS}s — escalating to SIGKILL",
    )
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=_KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def _write_note(capture, out_fd: int, line: str) -> None:
    # Make watcher actions visible in both the live stream and the capture
    # file, so a post-mortem read of the file explains abnormal endings.
    data = f"\n[coga watcher] {line}\n".encode()
    capture.write(data)
    capture.flush()
    try:
        os.write(out_fd, data)
    except OSError:
        pass


__all__ = ["run_headless"]
