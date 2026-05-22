---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Replace with the recurring task title"
# Pick a mode: `script` runs a skill script directly with no agent;
# `auto` is a one-shot headless agent run whose output is buffered to the
# task log; `interactive` drops into a human terminal with live output.
mode: script
workflow: namespace/your-workflow
owner: replace-with-human-name
assignee: replace-with-human-or-agent-nickname
---

## Description

What this recurring task does and why it runs on this cadence.

`relay recurring` (called from `scripts/cron.sh`) get-or-creates the current
period's task when this template's schedule is due. Files in `recurring/`
whose name starts with `_` are skipped — that's how this template stays inert.
