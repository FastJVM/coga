---
title: Blocker reminders
status: active
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 5247c684-c323-48fa-99b4-a52affbd7bf0
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
paused until the owner resumes it. Eligibility, recovery commands and the
one-attempt watermark are owned by
[coga/notifications/producers](context:coga/notifications/producers).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
