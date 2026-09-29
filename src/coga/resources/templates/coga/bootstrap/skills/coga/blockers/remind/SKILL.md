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
scans unresolved asks on blocked tasks and paused recurring periods, posts
owner reminders, and writes a compact `## Blocker reminders` watermark on
the affected task's blackboard. It never launches or reactivates the task.

Eligibility, recovery commands and deduplication are owned by
[coga/notifications/producers](context:coga/notifications/producers).
This includes an agent period whose block was followed by the recurring
runner's unfinished-run pause; its unresolved ask stays visible without
changing the pause or scheduler behavior.

The scanner and watermark writer live in `coga.blocker_reminders`; run them
with `coga run blocker-reminders`. Blocker creation and resolution stay owned
by `coga block` and `coga unblock`.
