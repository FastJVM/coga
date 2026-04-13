---
schedule: 0 9 1-3 * *
schedule_comment: 9am on the 1st/2nd/3rd of each month (script internally checks for first weekday)
project: admin
title: Brex unmapped transactions monthly count
mode: script
workflow: admin/script
owner: zach
contexts:
  - admin/bookkeeping
---

## Description

Open the Brex dashboard with the saved session, apply the Missing GL
account filter, download the xlsx, count rows where Posted Date falls
in the current month, and post a Slack message with the count.

Existing implementation lives in the `count-missing-gl.js` Playwright
script with a launchd wrapper that gates on "first weekday of the
month".

Migration:
1. Create `skills/admin/brex-unmapped/` with a `run.sh` that execs the
   current script.
2. Clone `workflows/admin/script.md` or point this template's frozen
   workflow to the new skill at create-time.
3. Move the launchd gating logic to the recurring cron schedule (or
   keep it in the wrapper — safer for now).

## Context

Threshold for action: if the count climbs above ~15, reach out to the
bookkeeper directly. See `admin/tax-automation` context.
