---
name: blocker-reminders/run
description: One-step lifecycle for the blocker-reminders recurring recipe.
steps:
  - name: remind
    skills:
      - coga/blockers/remind
    assignee: agent
---

## remind

Recipe-backed recurring task. `coga recurring` runs
`coga run blocker-reminders`, which scans `status: blocked` tasks,
posts owner reminders for unresolved blockers without a matching
`## Blocker reminders` watermark, and records that watermark on the blocked
task.
