---
title: Blocker reminders
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 4be57f26-ac67-4316-befb-c902cbacd12b
workflow:
  name: blocker-reminders/run
  steps:
  - name: remind
    skills:
    - coga/blockers/remind
    assignee: agent
step: 1 (remind)
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
paused until the owner resumes it.

### One attempt per blocker

`scan_blocker_reminders` includes `status: blocked` tasks and `status: paused`
period tasks under `tasks/recurring/` that still have unresolved `## Blockers`
asks. The latter covers an agent period whose block was followed by the
recurring runner's unfinished-run pause. Ordinary paused tickets, paused
periods without open asks, and terminal tasks are excluded. A human-paused
period with an open ask also qualifies: the ask remains visible, while the
reminder leaves status and scheduling untouched.

Blocked-task reminders point to `coga unblock <slug> --answer "..."`. Paused
period reminders name the paused status and point to `coga launch <slug>` to
review the ask, then `coga unblock <slug> --answer "..."` inside the resumed
session to record its answer. Direct unblock requires a blocked or
in-progress ticket ([lifecycle](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/lifecycle/SKILL.md)).

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

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
