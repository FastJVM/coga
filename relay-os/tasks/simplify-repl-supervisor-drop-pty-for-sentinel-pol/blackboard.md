The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implement — findings & plan

### Decision 1: byte-match channel — DELETE outright
Audited agent configs. `relay-os/relay.toml`, `example/relay-os/relay.toml`, and the
packaged template all define exactly two agents: `claude` and `codex`. Both are TUIs
that capture bash subprocess stdout into a private pipe, so the PTY byte-match
*physically cannot fire* for either. No shell-shaped agent is in scope. → Remove the
byte-match channel, `DONE_MARKER` constant, the emit-fallback print, and
`compose._defuse_done_marker` entirely. (Ticket's "delete it outright" branch.)

### Decision 2: idle_timeout activity tracking → wall-clock cap (option a)
With inherited stdio the supervisor no longer sees child/stdin bytes, so there is no
"activity" to reset against. Use elapsed wall-clock from session start as the cap.
Per ticket: `idle_timeout` is None for attended launches, so only unattended
`relay recurring` sweeps are affected, and a wall-clock cap is the right backstop there.

### Decision 3: poll latency → keep 0.25s
Keep `_SENTINEL_POLL_INTERVAL = 0.25` via `proc.wait(timeout=...)`. Worst-case chain
latency unchanged from today.

### Kept behaviors
Sentinel channel (`emit_done_marker`, `SENTINEL_ENV`, `_sentinel_signals_done`,
session-id scoping, atomic write, tempdir lifecycle); group kill + SIGTERM→SIGKILL
grace; `_classify_exit` (now fed a synthesized waitpid status from `proc.returncode`
so its semantics/tests are unchanged); `_TTY_SANITIZE` (now written to `sys.stdout`
since we no longer own a master fd); non-tty `subprocess.run` fallback.

### Files
- `src/relay/repl_supervisor.py` — rewrite: drop pty/select/termios/tty/fcntl/struct,
  `_resize_pty`, SIGWINCH, raw-mode, proxy loop, match buffer, `DONE_MARKER`,
  `marker`/`input_fd` params. Use `subprocess.Popen(start_new_session=True)` + poll.
- `src/relay/compose.py` — drop `_defuse_done_marker` + DONE_MARKER import; `prompt`
  returns assembled directly.
- `src/relay/commands/launch.py` — update stale DONE_MARKER comment; signature stable.
- Architecture context (both `relay-os/` + packaged template copy) — sentinel-poll model.
- Tests — see below.

NOTE: local interpreter is Python 3.9.12 (repo targets 3.11+ but uses
`from __future__ import annotations`, so tests run here).

## Dev
branch: sentinel-poll-supervisor
worktree: /home/n/Code/relay-sentinel-poll
commit: 45a0611 (not pushed — open-pr step handles that)

## Implement — outcome
Done. 8 files changed:
- `src/relay/repl_supervisor.py` — rewritten to `subprocess.Popen(start_new_session=True)`
  + sentinel poll. Dropped pty/select/termios/tty/fcntl/struct, `_resize_pty`, SIGWINCH,
  raw-mode, proxy loop, match buffer, `DONE_MARKER`, `marker`/`input_fd` params. Added
  `_status_from_returncode` so `_classify_exit` (and its tests) stays raw-waitpid-status
  based. `_TTY_SANITIZE` now written to stdout (`output_fd`). idle_timeout is now a flat
  wall-clock cap from launch. emit OSError branch is now silent (no print fallback).
- `src/relay/compose.py` — removed `_defuse_done_marker` + DONE_MARKER import; `prompt`
  returns assembled text unchanged.
- `src/relay/commands/launch.py` — comment updated; call signature unchanged.
- architecture SKILL.md (live + packaged template) — sentinel-poll model documented.
- 3 test files updated (byte-match test removed; helpers drop PTY framing/input_fd;
  emit-fallback test now asserts silence; compose test asserts token passes through).

### Verification
- `python -m pytest` → 569 passed, 1 skipped (ran in a fresh py3.12 venv in the
  worktree; system default python is 3.9 which can't install the pkg).
- `relay validate --json` against `example/` fixture → clean (no issues).
- No dangling refs to removed symbols; `relay.repl_supervisor`/`compose`/`launch`
  import clean.

### NOT done (later steps)
- No push / PR (that's `code/open-pr`).
- End-to-end manual verification with a real `claude` session and
  `relay recurring --interactive` (idle-timeout + done-signal) is in "Done looks like"
  but requires a real TTY + agent CLI — flag for the human / self-qa step. Automated
  tests exercise sentinel teardown, session-id scoping, idle-timeout, group kill,
  `_classify_exit`, and `_TTY_SANITIZE` on signal teardown.
