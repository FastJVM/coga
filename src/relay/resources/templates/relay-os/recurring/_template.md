---
# Files in recurring/ whose name starts with `_` are skipped by
# `relay create --check-recurring`. That's how this template stays inert.
# Copy this file (without the underscore) to author a real recurring task.

schedule: "0 9 * * 1"                 # cron, 5 fields (m h dom mon dow)
schedule_comment: "Every Monday at 9am"
title: "Weekly deliverability check"
mode: auto                            # auto | interactive | script
workflow: ops/check
project: email-tool                   # which project the new task lands in
owner: marc
assignee: claude1
contexts:
  - email/payment-flow
---

## Description

Run the full deliverability diagnostic suite.
Check SPF, DKIM, DMARC for all active domains.
Flag any new blacklist entries.
