---
name: coga/recurring/scheduling/failures
description: How a recurring sweep admits agent-backed periods, pauses unfinished and watchdog-stopped runs, isolates one template's failure, and chooses its exit code.
---

# Admission, unfinished runs, and failures

Part of [coga/recurring/scheduling](../SKILL.md).

## Admission and unfinished runs

Agent-backed periods (including `delegate:`) need stdin and stdout TTYs; a
headless sweep skips them with a warning, before creating a period or leaving a
materialized one untouched, and continues. The skipped template keeps its scan
row, `skip (agent needs a TTY)`, rather than a `## Template errors` entry; this
headless skip is not counted in `problems:`. A current period that is not
launchable (`canceled`, `blocked`, ...) is never refused: a durable checkout
would not launch it either. A `ticket.py` period runs headless
and is the shape for unattended schedulers.

A scheduled agent run must reach `done` in one launch. When an agent launch
returns unfinished — including a human/unassigned handoff or a `coga block` —
the sweep pauses it before continuing. The blocker-reminder job keeps open
asks on paused periods visible under its
[eligibility and deduplication contract](https://github.com/FastJVM/coga/blob/main/coga/recurring/blocker-reminders/ticket.md);
it does not resume them. Keep human gates and expected blockers out of scheduled
workflows. A **watchdog** pause (latest pause audit actor `system:watchdog`, not
superseded by a later human pause or creation) stays an unresolved failure:
every sweep that admits the template through the inactivity gate shows `needs attention (watchdog timeout)` with the resume command,
counts it in `problems:`, notifies, and exits non-zero after other work. Resume
with `coga launch recurring/<name>` or `coga mark active recurring/<name>`.

## Failures and exit code

One template's failure never cancels the rest: the sweep records it, runs every
later due template, names all failures, and exits with the first failing code.
A template that cannot be scanned (`## Template errors`: unloadable, bad ledger
record, failed create) is named on stderr, in the Slack alert, and in
`problems:`; on its own it does not change the exit code. A sweep with any
refused or errored template never reports "No recurring tasks due".
Two exits stop immediately: **75** (`git.RETRY_WITHOUT_SWEEP_EXIT_CODE`,
retained assist state needing reconciliation) and **≥ 128** (interrupt). Whatever
stops the loop, `recurring_runner._record_abandoned_due` names the stopping task
and each due task "admitted as due but never launched" in `problems:`.
Absence is a failure: an admitted watchdog recovery or a created period with no launch
outcome makes the sweep exit 2, except `skip (already handled on control)`.
A create sync to control that fails is non-fatal for the task — the created
period still launches — but it is named in `problems:` and exits 2. If the
created ticket then changed under that failed sync, the scan prints
`error (…)` for the template instead of any skip, and it never launches;
`--force` keeps the ordinary admission skip. A period adopted from control
stays `skip (already handled on control)` even when publishing its log line
fails; that failure is still named in `problems:`.
All of this is the sweep path.
The [autofix](../../autofix/SKILL.md) loop runs afterwards without changing the code.
