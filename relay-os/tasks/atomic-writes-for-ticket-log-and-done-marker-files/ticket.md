---
title: Atomic writes for ticket log and done-marker files
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
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
step: 4 (review)
---

## Description

Priority: low. Scoped honestly: in attended single-operator use this
barely matters — git is the backstop (`git checkout ticket.md` restores the
prior version) and a human is present to fix a truncated file. The ONLY place it
bites is unattended recurring: a crash mid-write at 3am corrupts `ticket.md`,
the next sweep's `relay validate` errors on it, and there is no human in the loop
until morning. So this is a fast-follow to recurring, bundled with the liveness
watchdog — and a legitimate wontfix if Relay never runs unattended. The fix is
cheap (`temp + os.replace`, a few lines), which is the main reason to just do it.

Task-state writes are not atomic:
- `Ticket.write` is a bare `path.write_text(self.render())` (`ticket.py:96-97`)
  — truncate-then-write. A crash mid-write (SIGKILL, disk full) leaves a
  truncated `ticket.md`, which is exactly the file `relay validate` then errors
  on.
- `append_log` is a plain `open("a")` (`logfile.py:22`) — fine for line-atomic
  appends within one host, but no fsync.
- `emit_done_marker` does `open(..., "w").write(...)` (`repl_supervisor.py:340`)
  — not atomic, no `os.replace`. The supervisor tolerates a partial read by
  waiting for the next poll on the session-id path, but the legacy bare-touch
  path (`session_id is None`) treats *any* existing file — including a zero-byte
  partial — as "done" and tears the agent down (`repl_supervisor.py:87-90`).
  That legacy path is a loaded footgun left in the API.

Fix: write via temp-file + `os.replace` (atomic rename) for `Ticket.write` and
the done-marker; consider fsync on the critical writes. Either remove the legacy
`session_id is None` bare-touch branch or make it safe.

Git history mitigates a corrupted ticket in practice, but "the validator errors
on the file we ourselves half-wrote" is avoidable.

Acceptance: ticket and done-marker writes are atomic (no observable truncated
state); the legacy bare-touch teardown path is removed or hardened; a test
simulates a partial/interrupted write and asserts the prior content survives.

## Context

Code: `src/relay/ticket.py:96-97`, `src/relay/logfile.py:22`,
`src/relay/repl_supervisor.py:340` (+ legacy path `:87-90`). Related but
separate: `file-locking-for-concurrent-task-mutation` (concurrency, not
atomicity).

Implementation notes (from evaluator review):
- Write the temp file in the *same directory* as the target so `os.replace`
  stays a true atomic rename (cross-filesystem rename degrades to copy).
- Prefer *hardening* the legacy `session_id is None` bare-touch branch (e.g.
  require non-empty content) over deleting it, unless a caller audit shows
  nothing relies on it — removal is a behavior change.
