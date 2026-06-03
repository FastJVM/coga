"""Run an agent REPL through a PTY and watch for an "I'm done" signal.

In interactive mode the agent's REPL doesn't exit on its own — the human
types `/exit`. For `relay recurring --interactive` (and any other unattended
caller of an interactive launch) we want the agent itself to be able to
signal completion so the next task can start without manual intervention.

Two signal channels, checked in parallel:

1. **Sentinel file** (primary). The supervisor creates a tempfile path and
   exports it as `RELAY_DONE_SENTINEL` in the child's env. `emit_done_marker`
   touches the file. Robust against TUI agents (Claude Code, Codex) that
   capture bash subprocess stdout into a private pipe rather than echoing it
   to the PTY — the PTY watcher never sees the marker bytes in that case.

2. **PTY byte match** (fallback). For shell-shaped agents that pipe stdout
   straight through, a literal match on `DONE_MARKER` in the PTY stream also
   triggers teardown.
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
import tempfile
import termios
import time
import tty
from pathlib import Path
from typing import Mapping

from relay.atomicio import atomic_write_text


# Unique sentinel — long enough that an agent's prose, code review, or
# context echo cannot collide with it by accident. Changing this is a
# breaking change for any agent context teaching the convention.
DONE_MARKER = b"<<<RELAY_SESSION_DONE_a9f3c41e>>>"

# Env var name the supervisor uses to advertise the sentinel-file path to
# the child. `emit_done_marker` reads this. Stable name = stable contract.
SENTINEL_ENV = "RELAY_DONE_SENTINEL"

# Grace period after SIGTERM before we escalate to SIGKILL. Claude Code and
# Codex respect SIGTERM, but a wedged or signal-trapping REPL would otherwise
# block the recurring sweep indefinitely.
_KILL_GRACE_SECONDS = 2.0

# How often the select loop wakes to poll the sentinel file. Cheap (a single
# stat) and bounds the worst-case autoquit latency to this interval.
_SENTINEL_POLL_INTERVAL = 0.25

# Terminal-sanitizing reset, emitted to the real terminal only when *we* tore
# the child down with a signal. A SIGTERM/SIGKILL'd TUI (Claude Code, Codex)
# never reaches its own atexit cleanup, so any output-side DEC private modes it
# enabled stay on after it dies. The `termios` restore below fixes line
# discipline (raw->cooked) but not these — left on, they make the keyboard look
# dead: input echoes to the wrong screen, arrow keys garble, pastes get
# wrapped, and the session reads as "hung" when the bump already succeeded. We
# undo the usual culprits (not a full `reset`, which would also clear
# scrollback the human may still want):
#   ?2004l bracketed paste     ?25h show cursor        ?1l normal cursor keys
#   >      normal keypad        ?1049l leave alt-screen ?1004l focus reporting
#   ?1000/1002/1003/1006/1015 l  mouse tracking (all encodings) off
# A child that exits on its own runs its own cleanup, so we skip this for it.
_TTY_SANITIZE = (
    b"\x1b[?2004l\x1b[?25h\x1b[?1l\x1b>"
    b"\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l"
    b"\x1b[?1004l\x1b[?1049l"
)


def _sentinel_signals_done(path: str, session_id: str | None) -> bool:
    """True when the sentinel file says *this* session is done.

    With no `session_id` the supervisor accepts any *non-empty* file (the
    legacy bare-touch contract, hardened): `emit_done_marker` always writes
    at least `"done\n"`, so a zero-byte file is necessarily a partial write
    rather than a finished signal and must not tear the session down. With a
    `session_id` the file's content must name this session — so an unrelated
    descendant that ran a session-ending `relay` command against a *different*
    ticket (e.g. a test fixture in a tempdir that inherited our
    `RELAY_DONE_SENTINEL`) is ignored. Either way a partial/empty read just
    misses this poll; the next one (≤`_SENTINEL_POLL_INTERVAL` later) sees the
    complete write.
    """
    if not os.path.exists(path):
        return False
    try:
        with open(path) as f:
            content = f.read().strip()
    except OSError:
        return False
    if session_id is None:
        return bool(content)
    return content == session_id


def run_with_done_marker(
    cmd: list[str],
    env: Mapping[str, str],
    marker: bytes = DONE_MARKER,
    *,
    session_id: str | None = None,
    output_fd: int | None = None,
    input_fd: int | None = None,
) -> int:
    """Spawn `cmd` in a PTY, proxy stdio, SIGTERM the child on done signal.

    Returns the child's exit code (0 if killed by the signal, or the natural
    exit code if the child exited on its own). Falls back to a plain
    `subprocess.run` if stdout is not a TTY — the watcher is only meaningful
    for interactive REPLs that wouldn't otherwise exit on their own.

    `session_id` scopes the sentinel-file channel to one session: the child's
    `emit_done_marker` writes this string into the file and the supervisor
    only tears down on a match. Leave it None for the legacy "any touch ends
    the session" behavior.

    `output_fd` / `input_fd` exist for tests; production callers leave them
    None and the supervisor proxies the real stdio.
    """
    if not sys.stdout.isatty():
        import subprocess

        return subprocess.run(cmd, env=dict(env), check=False).returncode

    sentinel_dir = tempfile.mkdtemp(prefix="relay-done-")
    sentinel_path = os.path.join(sentinel_dir, "sentinel")
    child_env = dict(env)
    child_env[SENTINEL_ENV] = sentinel_path

    pid, master_fd = pty.fork()
    if pid == 0:  # child
        for k, v in child_env.items():
            os.environ[k] = v
        try:
            os.execvp(cmd[0], cmd)
        except OSError:
            os._exit(127)

    _resize_pty(master_fd)

    out_fd = output_fd if output_fd is not None else sys.stdout.fileno()
    stdin_fd = input_fd if input_fd is not None else sys.stdin.fileno()

    def _notify(line: str) -> None:
        # Make the watcher's actions visible in the agent's own console so a
        # human can tell "the watcher stopped the REPL" apart from "the REPL
        # exited on its own". Only ever called when the watcher itself acts
        # (trigger / kill / final status), so it stays quiet on a normal
        # `/exit`. The terminal is in raw mode during proxying, so emit an
        # explicit `\r\n` to avoid staircasing; harmless once restored too.
        try:
            os.write(out_fd, f"\r\n[relay watcher] {line}\r\n".encode())
        except OSError:
            pass

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

    def _trigger_term(reason: str) -> None:
        nonlocal sent_term, term_deadline
        sent_term = True
        term_deadline = time.monotonic() + _KILL_GRACE_SECONDS
        _notify(f"stopping REPL — trigger={reason}")
        _notify("SIGTERM sent to process group")
        # `pty.fork()` puts the child in its own session, so the child PID
        # equals the process group id. Signal the whole group so any
        # foreground child (e.g. a `sleep` bash is currently waiting on, or
        # a tool the REPL spawned) also exits — otherwise SIGTERM to bash
        # gets queued until the foreground command returns.
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    try:
        while True:
            # After SIGTERM, give the child a grace period to exit; if it
            # ignores SIGTERM, escalate to SIGKILL so the sweep can move on.
            if sent_term and not sent_kill:
                timeout: float = max(0.0, (term_deadline or 0) - time.monotonic())
            else:
                timeout = _SENTINEL_POLL_INTERVAL
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
                _notify(
                    f"child still alive after {_KILL_GRACE_SECONDS}s — "
                    "escalating to SIGKILL"
                )
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

            if not sent_term and _sentinel_signals_done(sentinel_path, session_id):
                _trigger_term("sentinel-file (RELAY_DONE_SENTINEL touched)")

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
                    _trigger_term("pty-byte-match (DONE_MARKER seen in output)")
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
        # A child we signalled never ran its own terminal cleanup, so undo the
        # output-side DEC private modes it may have left enabled (see
        # `_TTY_SANITIZE`) — otherwise the shell underneath looks hung.
        if sent_term:
            try:
                os.write(out_fd, _TTY_SANITIZE)
            except OSError:
                pass
        signal.signal(signal.SIGWINCH, prev_winch)
        try:
            os.unlink(sentinel_path)
        except OSError:
            pass
        try:
            os.rmdir(sentinel_dir)
        except OSError:
            pass

    _, status = os.waitpid(pid, 0)
    code, notes = _classify_exit(status, sent_term)
    for note in notes:
        _notify(note)
    return code


def _classify_exit(status: int, sent_term: bool) -> tuple[int, list[str]]:
    """Map a raw `waitpid` status into (exit_code, console_notes).

    When we never signalled the child, its status passes straight through.
    When we *did* signal it, a death from our own SIGTERM/SIGKILL — or a
    self-exit — is the expected done-signal teardown and reports 0. But a
    death from some *other* signal means the watcher's stop raced a genuine
    crash; surface the real `128 + signal` code (and say so) instead of
    masking it as clean, so a watcher-adjacent crash stays visible.
    """
    if not sent_term:
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status), []
        if os.WIFSIGNALED(status):
            return 128 + os.WTERMSIG(status), []
        return 1, []

    if os.WIFSIGNALED(status):
        sig = os.WTERMSIG(status)
        if sig in (signal.SIGTERM, signal.SIGKILL):
            return 0, [
                f"child exited: killed by our signal {sig}",
                "reporting exit 0 (done-signal received)",
            ]
        return 128 + sig, [
            f"child exited: killed by signal {sig}",
            f"NOT our signal — real crash, reporting exit {128 + sig}",
        ]
    code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 0
    return 0, [
        f"child exited on its own with code {code} after our stop",
        "reporting exit 0 (done-signal received)",
    ]


def _resize_pty(master_fd: int) -> None:
    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        return
    try:
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except OSError:
        pass


def emit_done_marker(session_id: str | None = None) -> None:
    """Tell a supervising `run_with_done_marker` that this session is done.

    Writes `$RELAY_DONE_SENTINEL` if set (primary channel — survives TUI
    agents that capture bash subprocess stdout). Also prints `DONE_MARKER`
    on its own line (fallback channel for shell-shaped agents that echo
    stdout to the PTY). In a non-supervised terminal the printed line is
    harmless visible chrome and the env var is unset, so the file write is
    skipped.

    `session_id` is written as the file content so the supervisor can verify
    the signal names *its* session and ignore stray writes from unrelated
    descendants that merely inherited the env var. Session-ending commands
    pass the resolved task path (see `relay.commands.{bump,mark,panic}`); a
    bare call writes the legacy `"done"` sentinel.
    """
    sentinel = os.environ.get(SENTINEL_ENV)
    if sentinel:
        try:
            # Atomic so the supervisor's poll never observes a half-written
            # sentinel — the bare-touch path treats any non-empty file as
            # "done" (see `_sentinel_signals_done`).
            atomic_write_text(Path(sentinel), f"{session_id or 'done'}\n")
        except OSError:
            pass
    print(DONE_MARKER.decode("ascii"), flush=True)


__all__ = [
    "DONE_MARKER",
    "SENTINEL_ENV",
    "_TTY_SANITIZE",
    "emit_done_marker",
    "run_with_done_marker",
]
