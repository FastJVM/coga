---
schedule: "0 9 1-3 * *"
schedule_comment: "9am on the 1st/2nd/3rd of each month (script checks for first weekday)"
project: admin
title: "Xero monthly reconciliation"
mode: script
workflow: admin/script
owner: zach
contexts:
  - admin/bookkeeping
---

## Description

Run the Xero reconciliation automation. Clicks OK on all rule-matched
items, flags manual-attention items, and posts a Slack summary with
what was reconciled and what needs human review.

This recurring template is the fully-worked example — unlike the
other three, its skill already exists at `skills/admin/xero-reconcile/`
with a working `run.sh` wrapper around the existing Playwright
automation at `~/Desktop/Xero_Reconciliation_Automation`.

The frozen `admin/script` workflow already points at
`admin/xero-reconcile` as its default step skill, so no post-creation
edit is needed.

## Context

If Xero's DOM changes, selectors break and the script exits non-zero.
`relay launch` picks up the non-zero exit and posts the failure to
Slack. Fix the selectors in the automation directory before re-running.
