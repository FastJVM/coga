---
name: coga/blockers/remind
description: Re-notify owners about first-class blocked tasks and watermark reminders.
script: run.py
---

# Blocker Reminders

This skill is the script step for the `recurring/blocker-reminders` ticket. It
scans tasks whose frontmatter says `status: blocked`, reads their unresolved
`## Blockers` entries through Coga's shared blackboard parser, posts one live
owner reminder for each blocker that has not already been reminded, and writes
a compact `## Blocker reminders` watermark on the blocked task's own
blackboard.

The scanner and watermark writer live in `coga.blocker_reminders`; blocker
creation and resolution stay owned by `coga block` and `coga unblock`.
