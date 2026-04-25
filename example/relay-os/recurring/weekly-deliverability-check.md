---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Weekly deliverability check"
mode: auto
workflow: ops/check
project: email-tool
owner: marc
assignee: claude1
contexts:
  - email/payment-flow
---

## Description

Run the full deliverability diagnostic suite.
Check SPF, DKIM, DMARC for all active domains.
Flag any new blacklist entries.
