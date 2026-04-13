---
name: admin/xero-reconcile
description: Run the monthly Xero reconciliation script. Clicks OK on rule-matched items, flags manual-attention items, posts a Slack summary. Script-mode — no agent reasoning involved.
---

# Xero reconciliation

Script-mode skill. The bundled `run.sh` invokes the Playwright
automation at `~/Desktop/Xero_Reconciliation_Automation` which:

1. Opens Chromium with the saved Xero session.
2. Walks the reconciliation dashboard.
3. Clicks all OK buttons for rule-matched items.
4. Posts a Slack summary with:
   - What was reconciled (date, payee, amount per line)
   - What needs manual attention (with a link to the account page)

## Secrets needed

`SLACK_WEBHOOK_URL` — piped from `relay.local.toml` at launch time.

## Expected runtime

~2 minutes. The launchd gating logic (first weekday of month) lives
inside the automation directory, not in the relay task — the relay
side just fires the script whenever the recurring template says so.

## Failure mode

If Xero's DOM changes, the Playwright selectors break and `run.sh`
exits non-zero. `relay launch` picks up the non-zero exit and posts
the failure to the Slack feed. Manual intervention required — fix
the selectors in the automation directory, then rerun the task.
