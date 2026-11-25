---
name: coga/recurring/scheduling
description: How a recurring sweep runs due work — period keys and the serviced-period ledger, repo and clone scope, per-template status handling, phased launch order, the sweep variants and gates, TTY admission, unfinished runs, failures and the exit code; repo inactivity lives in its leaf.
---

# Recurring scheduling and sweeps

The repo-inactivity gate and `run_when_inactive` are in the leaf
[coga/recurring/scheduling/inactivity](inactivity/SKILL.md).

## Periods and the serviced-period ledger

The scan takes each template's last firing strictly before now and buckets it
into a period key: hourly → `YYYY-MM-DD-HH`, daily → `YYYY-MM-DD`, weekly
(day-of-week set) → `YYYY-Www`, monthly (day-of-month set) → `YYYY-MM`,
anything else → `YYYYMMDDTHHMM`. When the schedule fires more than once in
its month, week or day bucket (`0 9 * * 1-5`, `0 9 1,15 * *`, `0 9,17 * * *`),
the key steps down to the day, then the hour, so each firing gets its own
period; it never goes finer than an hour, so sub-hourly schedules keep one
period per hour.

The high-water mark is a `created|reused <task-ref> for <period>` line tagged
`recurring/<name>` in the repo-global `coga/log.md`. It is not in the template
blackboard, where a run rewriting a region could erase it and re-fire the
period. The greatest valid period evidence survives retention after a period task
is reaped and is never composed into prompts. A period at or below the newest valid record is not
re-created or re-launched. A malformed record is a template error in the
sweep, `coga recurring list` and `coga status`, never "ran this period".

Current period only: missed periods are not chased, so a monthly run of a
weekly template produces one run. A new template's first sweep services the
most recent past firing ([templates](../templates/SKILL.md#first-firing-is-retroactive)).

## Repo scope and clone scope

Repo-scoped jobs materialize a period task and use the checkout's local
ledger. Clone-scoped jobs use a machine-local ledger and launch their
template script directly. A configured recurring owner selects who runs the
repo's jobs.

## What a sweep does per template

A sweep walks the effective catalog, not the local directory: every
**enabled** job, local or bundled, per
[selection and state](../templates/SKILL.md#selection-and-state). Disabled,
parked and unselected jobs are not scheduled, and a selection or state error
is one template error that leaves healthy jobs running.

One stable task per template:

- **Live** (`active`, or orphaned `in_progress` from a dead supervisor) — resumed
  from its frozen period ticket; no duplicate. A stuck run defers new periods.
- **Current-period `done`** — skipped.
- **`paused`** — resumed from its frozen period ticket when the pause was not a
  human's (see [Admission and unfinished runs](#admission-and-unfinished-runs));
  a human pause is skipped. A paused run is never replaced because another
  period is due.
- **Prior-period `done`** (not reaped by Dream) — deleted, then a fresh `active`
  task is created at step 1 with a new blackboard, state snapshot and ledger
  record. The delete runs only after proving the replacement can be created
  (workflow and step skills resolve); otherwise it is one template error and the
  old task stays.
- **`canceled`** — terminal; see `--force`. Delete it to run again.

**Launch order is phased**: resumes (orphans and resumed pauses), then fresh launches, each
most-overdue first — and the cleanup template, Dream, always **last**, even as
an orphan, so its retro pass sees the period tasks this sweep just finished.
Launches are sequential. The sweep prints a scan table before launching.

## Variants

`coga recurring` scans the current checkout. `--all <path>` discovers workspaces
and scans each one in its own checkout. `--force` ignores the schedule and
reruns eligible work. `coga recurring launch <name>` runs a named template.
`--interactive` uses attended conduct for agent work.

## Admission and unfinished runs

The scan reads local templates, tickets and the serviced-period ledger. It
runs due tasks in sequence. Without a terminal, deterministic steps can run
and agent phases are refused. A scheduled session that times out or returns
with open work can be paused visibly for a later sweep. A ticket that records
a blocker stays blocked until it is answered.

## Failures and exit code

One template's failure never cancels the rest: the sweep records it, runs every
later due template, names all failures, and exits with the first failing code.
A resume that cannot activate its frozen agent or workflow is a per-period
refusal; the sweep continues with later templates.
A template that cannot be scanned (`## Template errors`: unloadable, bad ledger
record, failed create) is named on stderr, in the Slack alert, and in
`problems:`; on its own it does not change the exit code. A sweep with any
refused or errored template never reports "No recurring tasks due".
No launch exit code stops the loop: every due task launches in turn, and the
sweep exits with the first failing code.

Absence is a failure: a watchdog-paused period and a period this sweep created
with no launch outcome ("created this sweep but never launched") are each named
in `problems:`, and any such problem makes an otherwise clean sweep exit 2. All of this is the sweep path. The [autofix](../autofix/SKILL.md) loop
runs afterwards without changing the exit code.

Size exception: this topic stays over the size review thresholds, as
accepted when the recurring family was consolidated. It absorbed the former
serviced-period ledger and failures leaves; splitting it again would recreate
them, so only repo inactivity stays a separate leaf.

Retention preserves every occurrence of the greatest valid period per ref and
its winning creation/pause evidence, including absent or parked templates.
It validates the full ledger first and never erases malformed older evidence
to make a bounded reader succeed. Target-bound
reverse reads retain their at-least semantics and error reachability.
