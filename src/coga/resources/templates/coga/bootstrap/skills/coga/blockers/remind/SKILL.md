---
name: coga/blockers/remind
description: Re-notify owners about first-class blocked tasks and watermark reminders.
---

# Blocker Reminders

This skill documents the blocker-reminder sweep behind the
`recurring/blocker-reminders` ticket. That ticket's `ticket.py` runs the
registered `blocker-reminders` recipe
(`coga.blocker_reminders.run_blocker_reminders_recipe`) through
`coga.runner.run_recipe` — no agent, no composed prompt. The sweep
scans tasks whose frontmatter says `status: blocked`, reads their unresolved
`## Blockers` entries through Coga's shared blackboard parser, posts one live
owner reminder for each blocker that has not already been reminded, and writes
a compact `## Blocker reminders` watermark on the blocked task's own
blackboard.

That status filter is the sweep's only one, and it has a known blind spot: a
recurring **agent** period task that calls `coga block` does not stay
`blocked`. The scheduled-run contract in `coga/recurring/scheduling` requires an agent
run to reach `done` in one launch, so when the sweep gets control back it
rewrites the period `blocked → paused`
(`_stop_if_unfinished_after_launch` in `src/coga/recurring_runner.py`
returns early only for a script-recorded block). The unresolved ask then
sits on a `paused` ticket, fails this filter, and nobody is reminded.
`recurring/resolve-conflicts` recorded a TTY-admission blocker on 2026-08-13
and was paused the same minute, blocked and was paused again on 2026-08-14,
and the ask went unanswered until a human picked the paused task with
`coga megalaunch` on 2026-08-17. A deterministic `ticket.py` block *is*
covered — that lifecycle is preserved and the period stays `blocked`.
Widening the filter to `paused` tasks with unresolved asks was deliberately
not done (`paused` also means "a human parked this") and no ticket owns it;
check paused recurring periods by hand.

The scanner and watermark writer live in `coga.blocker_reminders`; run them
with `coga run blocker-reminders`. Blocker creation and resolution stay owned
by `coga block` and `coga unblock`.
