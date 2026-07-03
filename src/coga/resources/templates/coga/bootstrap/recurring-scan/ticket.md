---
title: Scan recurring templates and launch what's due
mode: script
script: run.py
assignee: claude
---

## Description

Stateless launch target for the recurring sweep. `coga recurring` (the thin
command head) parses `--interactive` / `--all`, writes them into a narrow env
contract (`COGA_RECURRING_FORCE` / `COGA_RECURRING_INTERACTIVE`), and launches
this target; `coga launch bootstrap/recurring-scan` runs the default
non-forced scan directly with no env set.

This is a bootstrap ticket, not a `tasks/` ticket and not a `recurring/`
template: it has no status, no workflow, no schedule, and no
`last_serviced_period` of its own. It cannot be a recurring template because it
is the thing that creates and launches recurring templates — a template that
scanned itself would be a bootstrap loop. Every launch is independent; the
run's only durable effects are the ones the scan makes to the real
`coga/recurring/<name>/` templates and their period tasks.

`run.py` loads config, reads the env contract, and calls
`coga.recurring_runner.run_recurring_scan`, which does the deterministic work:
scan `coga/recurring/`, get-or-create each due period's task, advance each
template's high-water mark, reconcile the creates onto the control branch, and
launch the due tasks sequentially. Adding or changing scan behavior is a normal
code change to `coga.recurring` / `coga.recurring_runner` / `coga.recurring_sync`,
not to this ticket.
