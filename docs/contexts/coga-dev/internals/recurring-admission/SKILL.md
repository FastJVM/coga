---
name: coga-dev/internals/recurring-admission
description: The admission machinery that keeps a stale, replaced or concurrently edited recurring period from starting, completing or parking work — period generations and leases, per-child refresh, direct-launch catch-up, the serviced-period ledger read, inactivity gate ordering, ledger freshness at create publication, and strict delegated publication and why delegation exists.
---

# Recurring admission

`recurring.scan_due` selects work from local templates, tickets and serviced
periods. `recurring_runner.run_recurring_scan` routes due tasks in sequence
and records outcomes. Template and launch dispatch both recognize step
scripts. Stateless delegates start through the same local launch service.

The configured recurring owner applies across entry points. Work remains in
the invoking checkout. `--all` starts each discovered checkout as its own
process.
