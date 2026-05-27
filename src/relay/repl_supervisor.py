"""Run an agent REPL through a PTY and watch for an "I'm done" marker.

In interactive mode the agent's REPL doesn't exit on its own — the human
types `/exit`. For `relay recurring --interactive` (and any other unattended
caller of an interactive launch) we want the agent itself to be able to
signal completion so the next task can start without manual intervention.

The convention: when an agent has finished its work for a task (after
`relay mark done`, `relay panic`, or any other terminal signal) it prints
the marker on its own line and the supervisor SIGTERMs the REPL.
"""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios
import time
import tty
from typing import Mapping


# Unique sentinel — long enough that an agent's prose, code review, or
# context echo cannot collide with it by accident. Changing this is a
# breaking change for any agent context teaching the convention.
DONE_MARKER = b"<<<RELAY_SESSION_DONE_a9f3c41e>>>"

# Grace period after SIGTERM before we escalate to SIGKILL. Claude Code and
# Codex respect SIGTERM, but a wedged or signal-trapping REPL would otherwise
# block the recurring sweep indefinitely.
_KILL_GRACE_SECONDS = 2.0


def run_with_done_marker(
    cmd: list[str],
    env: Mapping[str, str],
    marker: bytes = DONE_MARKER,
    *,
    output_fd: int | None = None,
    input_fd: int | None = None,
) -> int:
    """Spawn `cmd` in a PTY, proxy stdio, SIGTERM the child on marker.

    Returns the child's exit code (0 if killed by the marker, or the natural
    exit code if the child exited on its own). Falls back to a plain
    `subprocess.run` if stdout is not a TTY — the watcher is only meaningful
    for interactive REPLs that wouldn't otherwise exit on their own.

    `output_fd` / `input_fd` exist for tests; production callers leave them
    None and the supervisor proxies the real stdio.
    """
    if not sys.stdout.isatty():
        import subprocess

        return subprocess.run(cmd, env=dict(env), check=False).returncode

    pid, master_fd = pty.fork()
    if pid == 0:  # child
        for k, v in env.items():
            os.environ[k] = v
        try:
            os.execvp(cmd[0], cmd)
        except OSError:
            os._exit(127)

    _resize_pty(master_fd)

    out_fd = output_fd if output_fd is not None else sys.stdout.fileno()
    stdin_fd = input_fd if input_fd is not None else sys.stdin.fileno()
    old_attrs = None
    if os.isatty(stdin_fd):
        try:
            old_attrs = termios.tcgetattr(stdin_fd)
            tty.setraw(stdin_fd)
        except termios.error:
            old_attrs = None

    def _on_winch(_signum, _frame):  # type: ignore[no-untyped-def]
        _resize_pty(master_fd)

    prev_winch = signal.signal(signal.SIGWINCH, _on_winch)

    buf = bytearray()
    sent_term = False
    term_deadline: float | None = None
    sent_kill = False
    try:
        while True:
            # After SIGTERM, give the child a grace period to exit; if it
            # ignores SIGTERM, escalate to SIGKILL so the sweep can move on.
            if sent_term and not sent_kill:
                timeout: float | None = max(0.0, (term_deadline or 0) - time.monotonic())
            else:
                timeout = None
            try:
                rlist, _, _ = select.select(
                    [master_fd, stdin_fd], [], [], timeout
                )
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise

            if sent_term and not sent_kill and time.monotonic() >= (term_deadline or 0):
                sent_kill = True
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

            if master_fd in rlist:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    chunk = b""
                if not chunk:
                    break
                try:
                    os.write(out_fd, chunk)
                except OSError:
                    pass
                buf.extend(chunk)
                if not sent_term and marker in buf:
                    sent_term = True
                    term_deadline = time.monotonic() + _KILL_GRACE_SECONDS
                    # `pty.fork()` puts the child in its own session, so the
                    # child PID equals the process group id. Signal the
                    # whole group so any foreground child (e.g. a `sleep`
                    # bash is currently waiting on, or a tool the REPL
                    # spawned) also exits — otherwise SIGTERM to bash gets
                    # queued until the foreground command returns.
                    try:
                        os.killpg(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                # Bound the buffer but keep enough context to span chunks.
                if len(buf) > 4 * len(marker):
                    del buf[: -4 * len(marker)]
            if stdin_fd in rlist:
                try:
                    data = os.read(stdin_fd, 4096)
                except OSError:
                    data = b""
                if data:
                    os.write(master_fd, data)
    finally:
        if old_attrs is not None:
            try:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_attrs)
            except termios.error:
                pass
        signal.signal(signal.SIGWINCH, prev_winch)

    _, status = os.waitpid(pid, 0)
    if sent_term:
        # The agent told us it was done and we SIGTERMed the REPL. Treat
        # that as a clean exit regardless of the signal-death status code.
        return 0
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status)
    return 1


def _resize_pty(master_fd: int) -> None:
    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        return
    try:
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except OSError:
        pass


__all__ = ["DONE_MARKER", "run_with_done_marker"]
