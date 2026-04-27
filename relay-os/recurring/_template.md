---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Replace with the recurring task title"
mode: auto
workflow: namespace/your-workflow
owner: replace-with-human-name
assignee: replace-with-human-or-agent-nickname
---

## Description

What this recurring task does and why it runs on this cadence.

`relay recurring check` (called from `scripts/cron.sh`) creates a fresh
task on each scheduled firing. Files in `recurring/` whose name starts
with `_` are skipped — that's how this template stays inert.
