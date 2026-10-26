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
`ticket.py`, which scans blocked tasks and paused recurring periods with open asks,
posts owner reminders for unresolved blockers without a matching
`## Blocker reminders` watermark, and records that watermark on the task.
The scan leaves lifecycle state untouched; eligibility and recovery commands
are owned by [coga/notifications/producers](context:coga/notifications/producers).

## No other-agent code review

This is the one-step lifecycle of a recurring task's deterministic
half. It produces no code, so no `other-agent` step reviews it.
