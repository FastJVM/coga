---
schedule: "0 9 * * 1"                 # cron, 5 fields (m h dom mon dow)
schedule_comment: "Every Monday at 9am"
title: "Replace with the recurring task title"
mode: auto                            # auto | interactive | script
workflow: your-namespace/your-workflow
project: replace-with-project-name
owner: replace-with-human-name
assignee: replace-with-human-or-agent-nickname
# contexts:
#   - email/payment-flow
---

## Description

What this recurring task does and why it runs on this cadence.

`relay create --check-recurring` (called from `scripts/cron.sh`) creates
a fresh task in the configured project on each scheduled firing. Files
in `recurring/` whose name starts with `_` are skipped — that's how this
template stays inert.
