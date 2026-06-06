The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- branch: `fix/session-done-sentinel-and-mute`
- worktree: `/home/n/Code/relay-session-done-fix`
- commit: `cefd10e`

## Root cause

Both bugs trace to `emit_done_marker` in `src/relay/repl_supervisor.py`.

It signalled session-done over **two** channels on every `mark done` /
`bump` / `panic`:
1. the session-scoped **sentinel file** (`$RELAY_DONE_SENTINEL`) — the
   robust channel the supervisor polls; and
2. an **unconditional `print(DONE_MARKER)`** to stdout, billed as a
   "PTY-byte-match fallback for shell-shaped agents".

The file channel already covers *every* supervised agent (the supervisor
always exports the env var, regardless of agent shape), so the print was
redundant and only ever harmful:
- a TUI (Claude Code / Codex) captures the subprocess stdout into private
  tool output → the human sees the raw `<<<RELAY_SESSION_DONE_…>>>` (**Bug 1
  leak**);
- the supervisor's PTY watch never sees that captured print, so the file
  channel is what actually tears down — but in an **unsupervised** debug run
  (no env var) nothing consumes it, the REPL never tears down, and the
  harness issues a stray `Continue from where you left off` resume;
- when a TUI renders that captured marker back to its display, the unscoped
  bytes can cross-talk into a **parent** supervisor's PTY and tear the parent
  down (this is the duplicate ticket
  `session-done-sentinel-from-mark-done-bump-leaks-in`).

Bug 2 is the downstream effect: after the stray resume the agent saw
`status: done` and replied "No response requested" — going mute on a present
human because of task status.

## Fix

`emit_done_marker` now:
- writes the session-scoped sentinel file when supervised, and **does not**
  print the marker on success;
- prints the marker **only** as a last resort if the file write raises
  `OSError` (keeps the byte-match fallback for a shell-shaped agent whose
  file channel failed);
- emits **nothing** when unsupervised (no env var) — nothing watches, so a
  print would only leak the internal protocol string.

`src/relay/resources/prompt-interactive.md` gains a rule: a present human's
message always gets a real response; `status` governs the *workflow*, not
whether you talk to the person in front of you. "Exit cleanly — one step,
one session" = don't chain workflow steps, ≠ go silent.

## Resolves both reports

This change fixes both this ticket AND the duplicate
`session-done-sentinel-from-mark-done-bump-leaks-in` (the parent-orchestrator
cross-talk shared the same stray print). Per nick: note here + resolve the
two. The duplicate draft has been settled — see its blackboard for the
pointer.

## Tests

- `tests/test_done_marker_emission.py` — rewrote the three `_success_*`
  tests: the signal is asserted on the sentinel file (content == resolved
  task path), never in visible output; added unsupervised no-leak variants
  for bump / mark done / panic.
- `tests/test_repl_supervisor.py` — `writes_sentinel` now asserts the marker
  is *not* printed; added `prints_only_if_file_write_fails`; renamed
  `no_env_is_harmless` → `no_env_is_silent`.
- Full suite: **562 passed, 1 skipped** (run with the repo `.venv` py3.12,
  `PYTHONPATH=<worktree>/src`).

## Decisions / tradeoffs

- Shell-shaped agents lose the PTY-byte-match on the success path, but
  they're already torn down by the file channel (env var always set under a
  supervisor); the print survives only for the OSError edge. No real
  regression.
- Did not touch the supervisor's PTY byte-match in `run_with_done_marker` —
  it's harmless defense and still the channel the OSError fallback targets.
- `prompt-interactive.md` is a single core resource (not duplicated under
  `templates/relay-os/`), so no sync needed.

## Peer review

Ran `codex review --base main` from the feature worktree. Must-fix finding:
the shipped Relay architecture contexts still taught the old success-path
stdout marker contract. Applied the fix in both copies:
- `relay-os/contexts/relay/architecture/SKILL.md`
- `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`

The contexts now say normal teardown is the session-scoped
`$RELAY_DONE_SENTINEL` file, and the `DONE_MARKER` PTY byte-match is only a
last-resort fallback if writing the sentinel fails.

Verification after peer-review fix:
- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest tests/test_done_marker_emission.py tests/test_repl_supervisor.py -q` → 34 passed.
- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest -p no:cacheprovider` → 562 passed, 1 skipped.
