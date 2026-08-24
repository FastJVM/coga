---
name: blocker-reminders/run
description: One-step lifecycle for the blocker-reminders recurring task's deterministic half.
steps:
  - name: remind
    skills:
      - coga/blockers/remind
    assignee: agent
---

## remind

Script-backed recurring task. `coga launch` runs the period task's reserved
`ticket.py`, which scans `status: blocked` tasks,
posts owner reminders for unresolved blockers without a matching
`## Blocker reminders` watermark, and records that watermark on the blocked
task.
