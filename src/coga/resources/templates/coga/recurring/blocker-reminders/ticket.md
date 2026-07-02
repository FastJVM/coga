---
schedule: "0 10 * * *"
schedule_comment: "Every day at 10am - remind owners about unresolved blocker asks"
title: "Blocker reminders"
# A script step runs the reminder sweep directly with no agent: the workflow's
# one step references the `coga/blockers/remind` skill, whose `script:` calls
# `coga.blocker_reminders.remind_blocked_tasks`, with live console output of
# its own — no headless agent capture involved.
autonomy: auto
workflow: blocker-reminders/run
---

## Description

Remind owners about tasks stopped by `coga block`.

Agents stop through `coga block`, which appends an unresolved ask under
`## Blockers` and moves the ticket to `status: blocked`. The human answer
handshake stays command-owned: run `coga unblock <slug> --answer "..."`, then
launch or megalaunch can resume the task from the files.

Once a day this recurring script scans ordinary tasks, including recurring
period tasks, whose frontmatter says `status: blocked`. For each unresolved
blocker that has not already been reminded, it:

1. posts a live owner reminder naming the blocked task and the canonical
   `coga unblock <slug> --answer "..."` command shape,
2. writes a compact `## Blocker reminders` watermark on the blocked task's own
   blackboard, keyed by the blocker fingerprint, and
3. syncs the changed blocked task state through git.

The reminder state lives on the blocked task, not on this recurring task, so it
travels with the ask and stays inspectable in the same file a human edits to
answer it. The reminder job does not launch, unblock, or otherwise change task
selection; it only makes unresolved asks visible again.

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. Reminder
deduplication state is deliberately not stored here; each blocked task carries
its own `## Blocker reminders` watermark.
