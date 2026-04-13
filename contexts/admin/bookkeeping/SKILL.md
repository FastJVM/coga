---
name: admin/bookkeeping
description: Domain context for recurring bookkeeping automations — Brex unmapped transactions, Xero reconciliation, and similar monthly scrapers. Covers shared patterns (rule-matched vs manual-attention, Slack reporting, fragility) plus tool-specific facts. Attach to tickets that maintain or run bookkeeping automations.
---

# Bookkeeping automations — domain context

A family of monthly deterministic automations that keep the books
clean without requiring us to log in to each tool every month. They
share the same shape:

- **Cadence.** Fire on the first weekday of the month. The launchd
  wrapper gates by date; the Playwright / scraper code runs if the
  gate passes and exits silently otherwise.
- **Output.** A Slack summary with two lists: what was handled
  automatically (rule-matched) and what needs human attention
  (manual-review). The human reads the Slack post; the source data
  stays in the tool.
- **Fragility.** Every one of these is a UI scraper or dashboard
  click-driver, so DOM changes in the upstream tool break the
  automation. Failures post loudly to Slack. **A silent run is a
  successful run; an absent run is a failure.**

## Brex — unmapped transactions

Unmapped transactions accumulate when the bookkeeper forgets to
assign a GL account. The monthly job applies the "Accounting flag →
Missing GL account" filter, downloads the resulting xlsx, counts
rows posted in the current month, and posts a count to Slack.

- **Threshold for action:** if the count climbs above ~15, reach
  out to the bookkeeper directly. A creeping baseline is the
  early signal that something has changed in their workflow.
- **Not to touch:** the filter is saved on the Brex dashboard under
  the dashboard session. If the saved session expires, re-run
  the login flow in the automation directory before re-running
  the monthly job.

## Xero — reconciliation

The monthly reconciliation automation walks the Xero dashboard,
clicks OK on every rule-matched item, and flags anything that
doesn't match a rule as manual-attention. Slack output includes
date/payee/amount for each reconciled line and a direct link to
the account page for each flagged line.

- **Fragility point:** the Playwright selectors target Xero's
  reconciliation UI, which has changed shape twice in the last
  year. If the script exits non-zero, fix the selectors in
  `~/Desktop/Xero_Reconciliation_Automation` before re-running —
  do not wrap the error or retry blindly.
- **Never blind-click.** The script has an explicit allowlist of
  what kinds of rule matches are OK to auto-confirm. Expanding
  that list is a deliberate decision, not an automation tweak.

## Shared hygiene

- If a bookkeeping automation fails on the first of the month,
  **do not wait until next month to fix it.** Unmapped
  transactions and unreconciled lines compound — a one-month gap
  turns into a multi-hour manual cleanup. Treat these failures
  the same as a prod alert.
- When these automations change (new columns, new filters, new
  thresholds), update this context block **first**, then change
  the code. The context is what an agent reads to understand the
  domain; stale context causes silent wrong behavior more often
  than stale code does.
