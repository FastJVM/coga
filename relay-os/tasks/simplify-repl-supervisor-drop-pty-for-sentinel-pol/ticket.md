---
title: Simplify the REPL supervisor — drop the PTY for a sentinel-poll subprocess
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 2 (peer-review)
---

## Description

`relay launch` runs interactive agent REPLs through a full PTY supervisor
(`src/relay/repl_supervisor.py::run_with_done_marker`) so an agent can signal
"this session is done" and the launch loop can tear it down and chain the next
workflow step. The teardown has **two signal channels**:

1. **Sentinel file** (primary) — `emit_done_marker` writes the resolved task
   path into `$RELAY_DONE_SENTINEL`; the supervisor polls that file and
   `killpg`s the session on a match.
2. **PTY byte-match** (fallback) — a literal match on `DONE_MARKER` in the
   child's PTY output stream.

For the actual use case — a TUI agent (`claude`/`codex`) that signals done by
running `relay mark done` / `relay bump` / `relay panic`, after which launch
stops the session and starts the next step — **only the sentinel file ever
fires.** A TUI captures bash subprocess stdout into a private pipe, so
`emit_done_marker`'s output never reaches the PTY stream; the byte-match channel
*physically cannot trigger* for these agents (this is documented in the module
docstring as the very reason the file channel exists).

That makes the PTY pure overhead for the supported workflow. The entire
interpose apparatus — the `select` proxy loop copying bytes both directions,
`tty.setraw` on stdin, `_resize_pty`/`SIGWINCH` forwarding, the bounded
match buffer — exists *only* to observe the output stream for the byte-match
fallback. The complementary `compose._defuse_done_marker` (zero-width-joiner
hack so a prompt that quotes the marker can't tear the REPL down) exists only
because the PTY watches for those bytes. None of it is load-bearing when the
sole teardown signal is a side-channel file.

We want to replace the PTY supervisor with a plain subprocess that inherits the
real terminal and polls the sentinel file, deleting the byte-match channel and
its defenses — *unless* implement determines a real shell-shaped-agent case
still needs the byte-match (see Decisions).

## Context

### Why a plain subprocess is sufficient here

A child that **inherits** the real terminal (rather than being proxied through
a PTY) gets perfect interactivity for free — it owns the tty, so it handles its
own raw mode, resize, colors, and keyboard protocols directly. We don't need to
see its bytes for the supported teardown path; we only need to (a) notice the
sentinel file, (b) signal the whole process group, and (c) wait. Sketch:

    proc = subprocess.Popen(cmd, env=env, start_new_session=True)  # owns real TTY
    while proc.poll() is None:
        if _sentinel_signals_done(sentinel_path, session_id):
            os.killpg(proc.pid, signal.SIGTERM); ...   # grace -> SIGKILL
            break
        if idle_timeout and (now - last_activity) >= idle_timeout:
            os.killpg(proc.pid, signal.SIGTERM); break
        time.sleep(_SENTINEL_POLL_INTERVAL)

`start_new_session=True` gives the same killpg-able group `pty.fork()` did
(child is its own session leader, pid == pgid), so the group-kill semantics —
which matter so a `sleep`/tool the agent is blocked on also dies — are
preserved.

### What is kept

- **Sentinel-file channel** unchanged: `emit_done_marker`, `SENTINEL_ENV`,
  `_sentinel_signals_done`, session-id scoping, atomic write, tempdir lifecycle.
- **Group kill + SIGTERM→SIGKILL grace** (`_KILL_GRACE_SECONDS`).
- **`idle_timeout` backstop** for an agent that stalls/crashes before signalling.
- **`_classify_exit`** semantics (our-signal → exit 0; foreign signal → real
  `128+sig`).
- **`_TTY_SANITIZE`** — a SIGKILL'd TUI leaves DEC private modes / keyboard
  protocols on regardless of PTY-vs-inherit, so the terminal-repair write after
  a signal teardown still applies. (Re-verify it's emitted to the right fd now
  that we no longer own a master fd — likely `sys.stdout`.)
- **Non-tty fallback** to `subprocess.run` (already present).

### What is removed

- The PTY: `pty.fork`, master-fd plumbing, `_resize_pty`, `SIGWINCH` handler,
  `tty.setraw`/`termios` raw-mode dance, the stdin/stdout proxy loop, the
  match buffer.
- The **byte-match channel**: `match_token`, the `DONE_MARKER in buf` trigger,
  and the `pty-byte-match` reason — *pending the Decisions below*.
- `compose._defuse_done_marker` + `_DONE_MARKER_DEFUSED` (and its test), since
  nothing watches the PTY for the marker anymore — quoting it in a prompt is
  harmless. (Keep `DONE_MARKER` itself only if the byte-match is retained.)

### Decisions to settle during implement

- **Is any byte-match still required?** The fallback only earns its keep if
  Relay must support a *shell-shaped* agent that pipes stdout straight through
  **and** whose sentinel *file write* fails (`emit_done_marker`'s `OSError`
  branch). Audit `relay.toml` agent configs and the agent contexts: if every
  supported agent is a TUI covered by the file channel, delete the byte-match
  outright. If a shell-shaped agent is genuinely in scope, keep a minimal
  observe-only path (a pipe tee or a retained PTY *only* for that agent type)
  rather than carrying the full proxy for everyone. Record the call in the
  blackboard before ripping it out.
- **Activity tracking for `idle_timeout`.** The PTY loop reset `last_activity`
  on any PTY/stdin byte. With inherited stdio we no longer see those bytes.
  Options: (a) treat the timeout as a wall-clock cap from session start (simpler,
  slightly different semantics — a long *attended* think could trip it, but
  `idle_timeout` is None for attended launches today, so only unattended sweeps
  are affected); (b) approximate activity from sentinel-dir mtime or child CPU.
  Decide and document; (a) is likely fine given current callers.
- **Poll latency vs. responsiveness.** Keep `_SENTINEL_POLL_INTERVAL` (0.25s)
  via `time.sleep`/`proc.wait(timeout=...)`; confirm worst-case chain latency is
  acceptable.

### Files in scope

- `src/relay/repl_supervisor.py` — the rewrite (primary).
- `src/relay/compose.py` — drop `_defuse_done_marker` if byte-match goes.
- `src/relay/commands/launch.py` — caller; signature should stay stable
  (`run_with_done_marker(cmd, env, *, session_id, idle_timeout, ...)`), so the
  call site at `launch.py:427` ideally needs no change.
- `tests/` — update/replace PTY-specific tests; keep `output_fd`/`input_fd`
  test seams or replace with a subprocess-friendly equivalent. Add a test that
  a prompt quoting `DONE_MARKER` no longer needs defusing (or that defuse is
  gone). Keep coverage of: sentinel teardown, session-id scoping, idle-timeout,
  group kill, `_classify_exit`, `_TTY_SANITIZE` on signal teardown.

### Done looks like

- Interactive `relay launch` chains workflow steps exactly as before: claude
  runs `relay mark done`/`bump`, the session is torn down, the next step's
  agent launches as a fresh process. Manually verified end-to-end with a real
  `claude` session and via `relay recurring --interactive` (idle-timeout +
  done-signal both exercised).
- `repl_supervisor.py` is materially smaller (no PTY/proxy code) with the kept
  behaviors above intact.
- `python -m pytest` green; `relay validate --json` clean.
- Module docstring + any architecture context (`relay-os/contexts/relay/
  architecture/SKILL.md`) updated to describe the sentinel-poll model and the
  byte-match decision. Keep the live `relay-os/` copy and the packaged
  `src/relay/resources/templates/relay-os/` copy in sync.

### Risk / rollback

Single self-contained module behind a stable function signature; revert is one
commit. Main behavioral risk is terminal-state cleanup after a kill now that the
parent doesn't own a master fd — verify `_TTY_SANITIZE` still lands on the human
terminal and the shell is usable after an unattended teardown.
