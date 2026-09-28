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
paused until the owner resumes it. Eligibility, recovery commands and the
one-attempt watermark are owned by
[coga/notifications/producers](context:coga/notifications/producers).

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. Reminder
deduplication state is deliberately not stored here; each blocked task carries
its own `## Blocker reminders` watermark.
