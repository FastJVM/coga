---
name: blocker-reminders/run
description: One-step script workflow that reminds owners about unresolved task blockers.
steps:
  - name: remind
    skills:
      - coga/blockers/remind
    assignee: agent
---

## remind

Script step. Runs `coga/blockers/remind`, which scans `status: blocked` tasks,
posts owner reminders for unresolved blockers without a matching
`## Blocker reminders` watermark, and records that watermark on the blocked
task.
