---
schedule: "0 10 * * *"
schedule_comment: "Every day at 10am - remind owners about unresolved blocker asks"
title: "Blocker reminders"
# The reserved `ticket.py` sibling is this task's deterministic half: `coga
# launch` runs it directly, with no agent and no composed prompt. The one-step
# workflow keeps the period task's lifecycle and skill contract legible.
workflow: blocker-reminders/run
---

## Description

Remind owners about tasks stopped by `coga block`.

Agents stop through `coga block`, which appends an unresolved ask under
`## Blockers` and moves the ticket to `status: blocked`. The human answer
handshake stays command-owned: run `coga unblock <slug> --answer "..."`, then
launch or megalaunch can resume the task from the files.

Once a day this recurring task's `ticket.py` runs
`blocker_reminders.run_blocker_reminders_recipe`. It finds unresolved asks on
blocked tasks and paused recurring periods, posts an owner reminder, and
records a watermark on the affected task's blackboard before syncing it.

The reminder does not launch or reactivate work. A paused period remains
paused until its ask is answered; the next sweep then resumes a period the
sweep itself parked.

### One attempt per blocker

`scan_blocker_reminders` includes `status: blocked` tasks and `status: paused`
period tasks under `tasks/recurring/` that still have unresolved `## Blockers`
asks. The latter covers an agent period whose block was followed by the
recurring runner's unfinished-run pause. Ordinary paused tickets, paused
periods without open asks, and terminal tasks are excluded. A human-paused
period with an open ask also qualifies: the ask remains visible, while the
reminder leaves status and scheduling untouched.

Every reminder points to `coga unblock <slug> --answer "..."`. Paused period
reminders name the paused status and say the next recurring sweep resumes the
period: unblock resolves a paused period's asks without changing its status,
and a sweep-paused period with no open asks left is resumed
([lifecycle](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/lifecycle/SKILL.md),
[scheduling](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/recurring/scheduling/SKILL.md#admission-and-unfinished-runs)).
A human-paused period stays paused after its asks are answered.

`remind_blocked_tasks` posts one reminder per unresolved blocker, then
`record_reminder` appends a `- <fingerprint> last_reminded: <stamp>` line
under `## Blocker reminders` on the task's blackboard. The fingerprint is a
**permanent dedup key, not a cooldown**: a watermarked blocker is never
reminded again, including after a blocked-to-paused transition.

The post uses the default `fatal=True`, so the watermark is written only after
`post` returns:

- a delivered post, or a post that returned without delivering because no
  channel is selected or Slack is disabled, burns the one attempt — the
  blocker can be watermarked with nobody told;
- a delivery failure or unresolved webhook exits the run before the
  watermark, so that blocker is retried on the next sweep.

A sweep printing `no unresolved blockers to remind` may mean every open ask is
already watermarked; read the eligible tasks, not the exit line. Re-reminding
on an interval, or watermarking only confirmed deliveries, would be a behavior
change.

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. Reminder
deduplication state is deliberately not stored here; each blocked task carries
its own `## Blocker reminders` watermark.
