---
title: Session-done sentinel leaks and agent stops responding to a present human
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
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
step: 1 (implement)
---

## Description

Two coupled bugs observed at the end of a `relay-dev-update` debug run
(2026-06-05), both around session teardown after `relay mark done`. They
showed up together, so capturing them as one ticket.

### Bug 1 — the session-done sentinel leaks *and* doesn't actually tear down

When the run called `relay mark done`, the command emitted the supervisor's
teardown signal `<<<RELAY_SESSION_DONE_a9f3c41e>>>` **into visible output**
(the known `session-done-sentinel-...-leaks-in` leak), and then — instead of
the REPL being torn down — the session received a generic
`Continue from where you left off` resume prompt and kept going.

So the sentinel is doing neither job cleanly: it's visible to the human when
it should be consumed by the supervisor, and it does *not* result in the
teardown it's supposed to signal. Either the supervisor isn't consuming the
marker on `mark done` (only on supervised `bump`?), or the marker is written
to a stream the supervisor doesn't read, so the session falls through to a
plain resume.

### Bug 2 — the agent goes silent on a present human because status is `done`

After that stray resume, the agent checked the ticket, saw `status: done`,
concluded "nothing left to do," and replied **"No response requested"** —
i.e. it stopped responding *because of task status*, while the human was
still actively typing in the terminal.

In **interactive mode** a present human's prompt must win over a status
check. The base prompt's "one step, one session — exit cleanly" rule is about
not *chaining to the next workflow step*; it is not license to go mute on a
live human who keeps talking. Gating responsiveness on `status` means the
agent goes quiet exactly when the human is mid-conversation — the worst time.

### Why they're one ticket

Bug 1 produces the stray resume that Bug 2 then mishandles. A clean teardown
on `mark done` would have prevented the bad resume entirely; failing that, the
agent should still answer the human rather than treat `done` as a stop signal.
Fixing only one leaves a bad path: fix the sentinel but not the agent, and any
other stray resume still goes mute; fix the agent but not the sentinel, and
the teardown marker keeps leaking to users.

### Repro (observed)

1. Run a no-workflow recurring task to completion (`relay-dev-update` debug
   run); finish with `relay mark done <task>`.
2. Observe `<<<RELAY_SESSION_DONE_...>>>` printed in the visible transcript.
3. Observe the session is *not* torn down — a `Continue from where you left
   off` prompt arrives.
4. The agent responds `No response requested` / goes silent; subsequent human
   messages are at risk of the same because the task is now `done`.

### Sketch of a fix (refine in implement)

- Sentinel: ensure `mark done` (not just supervised `bump`) routes the
  teardown marker to the channel the supervisor consumes, and that it never
  reaches user-visible output. Confirm whether teardown-on-`mark done` is
  wired at all for no-workflow tasks. (Overlaps the existing
  `session-done-sentinel-from-mark-done-bump-leaks-in` ticket — dedupe or
  fold that in.)
- Agent behavior: in interactive mode, a present human's message always gets
  a real response; never substitute "No response requested" based on
  `status` being `done`/`in_progress`. Exiting cleanly means not *chaining
  steps*, not refusing to talk to the human in front of you.

## Context

