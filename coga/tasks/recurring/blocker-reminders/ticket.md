---
slug: recurring/blocker-reminders
title: Blocker reminders
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
period_generation: ed1fde88-9e61-4acc-87af-dd67f5bb5be1
workflow:
  name: blocker-reminders/run
  steps:
  - name: remind
    skills:
    - coga/blockers/remind
    assignee: agent
secrets: null
step: 1 (remind)
---

## Description

Remind owners about tasks stopped by `coga block`.

Agents stop through `coga block`, which appends an unresolved ask under
`## Blockers` and moves the ticket to `status: blocked`. The human answer
handshake stays command-owned: run `coga unblock <slug> --answer "..."`, then
launch or megalaunch can resume the task from the files.

Once a day this recurring task's `ticket.py` scans tasks whose frontmatter says
`status: blocked` — `run_blocker_reminders_recipe` in
`src/coga/blocker_reminders.py` filters on exactly that status and on nothing
else. For each unresolved blocker that has not already been reminded, it:

1. posts a live owner reminder naming the blocked task and the canonical
   `coga unblock <slug> --answer "..."` command shape,
2. writes a compact `## Blocker reminders` watermark on the blocked task's own
   blackboard, keyed by the blocker fingerprint, and
3. syncs the changed blocked task state through git.

The reminder state lives on the blocked task, not on this recurring task, so it
travels with the ask and stays inspectable in the same file a human edits to
answer it. The reminder job does not launch, unblock, or otherwise change task
selection; it only makes unresolved asks visible again.

### What this scan does not cover

A recurring **agent** period task that calls `coga block` does not stay
`blocked` long enough to be scanned. The scheduled-run contract in the
`coga/recurring` context requires an agent run to reach `done` in one launch,
so when the sweep gets control back it rewrites the period `blocked → paused`;
`_pause_unfinished` in `src/coga/recurring_runner.py` returns early for a
script-recorded block and never for an agent one. The unresolved ask is still
sitting on the paused ticket, but `status: paused` fails this scan's only
filter, so nobody is reminded of it and the only surface that would have is
blind to it. That is what happened to `recurring/resolve-conflicts`: it
recorded a TTY-admission blocker on 2026-08-13 and was paused in the same
minute (`paused (blocked → paused) — Agent recurring launch exited unfinished`
in `coga/log.md`), blocked and was paused again on 2026-08-14, and the ask sat
unanswered until a human explicitly picked the paused task with
`coga megalaunch` on 2026-08-17. No reminder fired in between, and none would
have.

A deterministic `ticket.py` phase that records a blocker *is* covered — that
lifecycle signal is deliberately preserved and the period task stays `blocked`.

So a paused recurring period task carrying an unresolved blocker is
human-parked debt no reminder covers. Widening the filter to include `paused`
tasks that still carry unresolved asks is a real design change, not a bug fix —
`paused` also means "a human deliberately parked this" — and is not implemented
here. Do not read this template as covering it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
