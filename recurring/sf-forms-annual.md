---
schedule: "0 9 1-7 1 *"
schedule_comment: "9am each weekday in the first week of January (script checks for first weekday)"
project: admin
title: "Annual state and federal tax forms download"
mode: script
workflow: admin/script
owner: zach
contexts:
  - admin/tax-automation
---

## Description

Log in to Gusto, navigate to Tax Documents, download the prior year's
federal and state forms, save them to the `{Year} Tax Year` folder in
Google Drive, and post a Slack confirmation.

Forms downloaded (for the previous tax year):
- Form 941 (Federal Payroll Tax) — Q1 through Q4
- Form 940 (Federal Unemployment / FUTA) — Annual
- DE-9 (CA State Taxes) — Q1 through Q4

Migration:
1. Create `skills/admin/sf-forms-download/` with a `run.sh` that execs
   the current Playwright automation.
2. Frozen workflow points at the new skill at task-creation time.

## Context

Runs once per year. Launchd currently fires every weekday in January
and the script internally gates on "Jan 1 or first weekday after". The
cron expression above matches that pattern and leaves the gating logic
in the script for safety.

Gusto UI changes have broken this automation twice before — the
failure Slack is the only signal. See `admin/tax-automation` context.
