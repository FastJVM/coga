"""Run an agent REPL through a PTY and watch for an "I'm done" signal.

In interactive mode the agent's REPL doesn't exit on its own — the human
types `/exit`. For `coga recurring --interactive` (and any other unattended
caller of an interactive launch) we want the agent itself to be able to
signal completion so the next task can start without manual intervention.

The signal travels over a single **sentinel file**. The supervisor creates a
tempfile path and exports it as `COGA_DONE_SENTINEL` in the child's env;
`emit_done_marker` writes the launched session's id into it and the supervisor
polls for that match. The file channel is robust against TUI agents (Claude
Code, Codex) that capture bash subprocess stdout into a private pipe rather
than echoing it to the PTY, and — because its content names the session — it
never tears down a *different* session that merely inherited the env var.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from coga.atomicio import atomic_write_text


# Env var name the supervisor uses to advertise the sentinel-file path to
# the child. `emit_done_marker` reads this. Stable name = stable contract.
SENTINEL_ENV = "COGA_DONE_SENTINEL"

# Grace period after SIGTERM before we escalate to SIGKILL. Claude Code and
# Codex respect SIGTERM, but a wedged or signal-trapping REPL would otherwise
# block the recurring sweep indefinitely.
_KILL_GRACE_SECONDS = 2.0

# How often the select loop wakes to poll the sentinel file. Cheap (a single
# stat) and bounds the worst-case autoquit latency to this interval.
_SENTINEL_POLL_INTERVAL = 0.25

# Exit code reported when *we* tore the REPL down because it exceeded a liveness
# limit (idle-output or max-session wall-clock) without ever signalling done.
# 124 is the `timeout(1)` convention — a non-zero code distinct from a clean
# done (0) so a caller can tell a wedge apart from a cooperative teardown.
_TIMEOUT_EXIT_CODE = 124


@dataclass(frozen=True)
class ReplOutcome:
    """How a supervised REPL ended.

    `exit_code` is what the caller should propagate (0 for a clean done,
    `_TIMEOUT_EXIT_CODE` for a liveness teardown, `128 + signal` for a crash,
    or the child's own code when it exited on its own). `kind` names *why* it
    ended so a caller can branch without re-deriving it from the number:

    - `"natural"` — the child exited on its own; we never signalled it.
    - `"done"` — we tore it down after a sentinel-file done signal.
    - `"timeout"` — we tore it down on a liveness limit (idle / max-session);
      the agent never signalled done. This is the wedge the watchdog catches.
    - `"crash"` — a death by a signal we did **not** send, surfaced rather than
      masked even when it raced our own teardown.
    """

    exit_code: int
    kind: str


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
# The keyboard-input protocols are a separate family: unlike the DEC private
# modes above they reshape what bytes the *keyboard* sends, so a leftover one
# turns every keypress into an escape report (e.g. `\x1b[5;1:3u`) and the shell
# beneath looks like its keys are dead. We clear both:
#   <u  + =0;1u   kitty keyboard protocol — pop the stack, then force flags to 0
#                 (covers both push/pop users and the set-flags form)
#   >4;0m         xterm modifyOtherKeys off
# Unsupported sequences are silently ignored by terminals that lack them.
# A child that exits on its own runs its own cleanup, so we skip this for it.
_TTY_SANITIZE = (
    b"\x1b[?2004l\x1b[?25h\x1b[?1l\x1b>"
    b"\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l"
    b"\x1b[?1004l\x1b[?1049l"
    b"\x1b[<u\x1b[=0;1u\x1b[>4;0m"
)


def _sentinel_signals_done(path: str, session_id: str | None) -> bool:
    """True when the sentinel file says *this* session is done.

    With no `session_id` the supervisor accepts any *non-empty* file (the
    legacy bare-touch contract, hardened): `emit_done_marker` always writes
    at least `"done\n"`, so a zero-byte file is necessarily a partial write
    rather than a finished signal and must not tear the session down. With a
    `session_id` the file's content must name this session — so an unrelated
    descendant that ran a session-ending `coga` command against a *different*
    ticket (e.g. a test fixture in a tempdir that inherited our
    `COGA_DONE_SENTINEL`) is ignored. Either way a partial/empty read just
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
    *,
    session_id: str | None = None,
    idle_timeout: float | None = None,
    max_session: float | None = None,
    output_fd: int | None = None,
    input_fd: int | None = None,
    cwd: "os.PathLike[str] | str | None" = None,
) -> ReplOutcome:
    """Spawn `cmd` in a PTY, proxy stdio, SIGTERM the child on done signal.

    Returns a `ReplOutcome` carrying the exit code *and* the reason it ended
    (`natural` / `done` / `timeout` / `crash`) so the caller can tell a
    cooperative teardown apart from a liveness wedge without inspecting the
    number. Falls back to a plain `subprocess.run` if stdout is not a TTY — the
    watcher is only meaningful for interactive REPLs that wouldn't otherwise
    exit on their own.

    `session_id` scopes the sentinel-file channel to one session: the child's
    `emit_done_marker` writes this string into the file and the supervisor
    only tears down on a match. Leave it None for the legacy "any touch ends
    the session" behavior.

    `idle_timeout`, when set, is a backstop for a REPL that never signals done
    — an agent that stalls or crashes before reaching `coga bump` / `mark
    done` / `panic`. If no PTY output and no stdin reaches the loop for that
    many seconds, the supervisor tears the REPL down (a `timeout` outcome,
    exit `_TIMEOUT_EXIT_CODE`) instead of blocking its caller forever. Leave it
    None to wait indefinitely for the done signal — the default, so an attended
    interactive session is never killed mid-think. Unattended sweeps
    (`coga recurring`) arm it so one stuck agent can't starve later tasks.

    `max_session`, when set, is a wall-clock cap measured from spawn. It fires
    even while the child is *still producing output* — the case idle-timeout
    misses, e.g. an agent stuck in an output-producing loop that keeps the PTY
    busy but never signals done. Also a `timeout` outcome. Leave None for no
    wall-clock cap.

    `cwd`, when set, is the working directory the child runs in — the per-launch
    `git worktree` under `[launch].worktree` isolation. None runs in the
    supervisor's own cwd (today's behaviour).

    `output_fd` / `input_fd` exist for tests; production callers leave them
    None and the supervisor proxies the real stdio.
    """
    if not sys.stdout.isatty():
        import subprocess

        code = subprocess.run(
            cmd, env=dict(env), check=False, cwd=cwd
        ).returncode
        return ReplOutcome(code, "natural")

    sentinel_dir = tempfile.mkdtemp(prefix="coga-done-")
    sentinel_path = os.path.join(sentinel_dir, "sentinel")
    child_env = dict(env)
    child_env[SENTINEL_ENV] = sentinel_path

    pid, master_fd = pty.fork()
    if pid == 0:  # child
        for k, v in child_env.items():
            os.environ[k] = v
        if cwd is not None:
            try:
                os.chdir(cwd)
            except OSError:
                os._exit(127)
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
            os.write(out_fd, f"\r\n[coga watcher] {line}\r\n".encode())
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

    sent_term = False
    term_kind: str | None = None
    term_deadline: float | None = None
    sent_kill = False
    session_start = time.monotonic()
    last_activity = session_start

    def _trigger_term(reason: str, *, kind: str) -> None:
        nonlocal sent_term, term_kind, term_deadline
        sent_term = True
        term_kind = kind
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
                _trigger_term(
                    "sentinel-file (COGA_DONE_SENTINEL touched)", kind="done"
                )

            if (
                idle_timeout is not None
                and not sent_term
                and time.monotonic() - last_activity >= idle_timeout
            ):
                _trigger_term(
                    f"idle-timeout (no REPL activity for {idle_timeout:.0f}s)",
                    kind="timeout",
                )

            if (
                max_session is not None
                and not sent_term
                and time.monotonic() - session_start >= max_session
            ):
                _trigger_term(
                    f"max-session (wall-clock exceeded {max_session:.0f}s)",
                    kind="timeout",
                )

            if master_fd in rlist:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    chunk = b""
                if not chunk:
                    break
                last_activity = time.monotonic()
                try:
                    os.write(out_fd, chunk)
                except OSError:
                    pass
            if stdin_fd in rlist:
                try:
                    data = os.read(stdin_fd, 4096)
                except OSError:
                    data = b""
                if data:
                    os.write(master_fd, data)
                    last_activity = time.monotonic()
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
    code, kind, notes = _classify_exit(status, term_kind)
    for note in notes:
        _notify(note)
    return ReplOutcome(code, kind)


def _classify_exit(
    status: int, term_kind: str | None
) -> tuple[int, str, list[str]]:
    """Map a raw `waitpid` status into (exit_code, kind, console_notes).

    `term_kind` is why *we* tore the child down: None when we never signalled
    it (its status passes straight through as a `natural` exit), `"done"` when
    a done signal released it, `"timeout"` when a liveness limit did.

    When we did signal it, a death from our own SIGTERM/SIGKILL — or a
    self-exit after our signal — is the expected teardown: it reports 0 for a
    `done` teardown and `_TIMEOUT_EXIT_CODE` for a `timeout` one, so a wedge is
    visibly non-zero rather than masquerading as a clean done. But a death from
    some *other* signal means the watcher's stop raced a genuine crash; surface
    the real `128 + signal` code as a `crash` (and say so) regardless of why we
    were tearing down, so a watcher-adjacent crash stays visible.
    """
    if term_kind is None:
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status), "natural", []
        if os.WIFSIGNALED(status):
            return 128 + os.WTERMSIG(status), "crash", []
        return 1, "crash", []

    if term_kind == "timeout":
        teardown_code = _TIMEOUT_EXIT_CODE
        teardown_label = "timeout — liveness limit, agent never signalled done"
    else:
        teardown_code = 0
        teardown_label = "done-signal received"

    if os.WIFSIGNALED(status):
        sig = os.WTERMSIG(status)
        if sig in (signal.SIGTERM, signal.SIGKILL):
            return teardown_code, term_kind, [
                f"child exited: killed by our signal {sig}",
                f"reporting exit {teardown_code} ({teardown_label})",
            ]
        return 128 + sig, "crash", [
            f"child exited: killed by signal {sig}",
            f"NOT our signal — real crash, reporting exit {128 + sig}",
        ]
    code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 0
    return teardown_code, term_kind, [
        f"child exited on its own with code {code} after our stop",
        f"reporting exit {teardown_code} ({teardown_label})",
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

    The signal travels over the **sentinel file** (`$COGA_DONE_SENTINEL`):
    a session-scoped, side-channel write the supervisor polls. It survives
    TUI agents (Claude Code, Codex) that capture bash subprocess stdout into
    a private pipe, and — because its content names the session — it never
    tears down a *different* session that merely inherited the env var (e.g.
    a parent orchestrator marking a child task done).

    The sentinel file is the *only* channel: there is deliberately no
    in-band stdout signal. An earlier design printed the done marker to
    stdout as a fallback, but it was unscoped to the session and actively
    harmful — a TUI captures the print into visible tool output (the human
    sees the raw teardown marker), and when a TUI renders that captured
    output back to its display the bytes can cross-talk into a *parent*
    supervisor's PTY and tear the parent down. If the file write fails there
    is nothing left to fall back to; the supervisor's idle/max-session
    backstop catches a session that never signalled done.

    `session_id` is written as the file content so the supervisor can verify
    the signal names *its* session and ignore stray writes from unrelated
    descendants that merely inherited the env var. Session-ending commands
    pass the resolved task path (see `coga.commands.{bump,mark,panic}`); a
    bare call writes the legacy `"done"` sentinel.
    """
    sentinel = os.environ.get(SENTINEL_ENV)
    if not sentinel:
        # No supervisor is watching (e.g. a bare `claude`/`codex` session, or
        # a debug run outside `coga launch`). Emitting the marker here would
        # only print the internal teardown string into the human's visible
        # transcript with nothing to consume it. Stay silent.
        return
    try:
        # Atomic so the supervisor's poll never observes a half-written
        # sentinel — the bare-touch path treats any non-empty file as
        # "done" (see `_sentinel_signals_done`).
        atomic_write_text(Path(sentinel), f"{session_id or 'done'}\n")
    except OSError:
        # The sentinel file is the only channel; if its write fails there is
        # nothing to fall back to. The session degrades to the supervisor's
        # idle/max-session backstop rather than signalling done in-band.
        pass


__all__ = [
    "SENTINEL_ENV",
    "_TIMEOUT_EXIT_CODE",
    "_TTY_SANITIZE",
    "ReplOutcome",
    "emit_done_marker",
    "run_with_done_marker",
]
