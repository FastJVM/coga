---
name: admin/tax-automation
description: Domain context for tax-specific automations — the IRC §41 R&D credit running doc and the annual Gusto payroll forms download. Attach to tickets that maintain or run tax-related scripts. For general bookkeeping automations (Brex, Xero), attach admin/bookkeeping instead.
---

# Tax automation — domain context

Scoped to automations that directly produce tax filings or feed the
year-end tax workflow. Bookkeeping hygiene (Brex unmapped, Xero
reconciliation) lives in `admin/bookkeeping` — attach that instead
for general monthly scrapers.

## IRC §41 R&D credit

We maintain a running document (`rd_tax_<year>.md`) of qualifying R&D
activity throughout the year, so year-end filing is a review-and-sign
instead of a reconstruction.

**Qualifying projects (current):**
1. SuperVM / Staticizer / Loop Parallelizer
2. Relay (this system — AI agent coordination framework)
3. Monero / Solar applied compiler research
4. invokeoptim / OpenJDK (Marcus)

**Explicitly excluded from qualifying activity:**
- Website work (marketing site, landing pages)
- Internal automations (Brex, Xero, Gusto scrapers — including this one)
- Admin, accounting, meetings
- Support and customer-facing bug fixes

The classification prompt in the rd-tax automation encodes these
rules. Any new project must be explicitly added to the prompt with
justification.

## Gusto tax forms

Annual download of DE-9 (CA), 941 (federal payroll), 940 (FUTA).
Runs on the first weekday of January for the previous tax year.
Output goes to `{Year} Tax Year` folder in shared Google Drive.

**If Gusto changes their UI** (happened twice in 2025), the Playwright
selectors break. The automation will fail loudly via Slack — do not
ignore those failures, they are the only signal you get.
