---
name: coga/recurring/scheduling
description: How a recurring sweep decides and runs due work — period keys and the log ledger, launch order, per-status handling, --force, named and --all launches, the owner gate, TTY admission, unfinished runs, and the sweep's exit code.
---

# Recurring scheduling and sweeps

## Periods and the serviced-period ledger

The scan takes each template's last firing strictly before now
(`recurring._last_firing`) and buckets it (`_period_key`): hourly →
`YYYY-MM-DD-HH`, daily → `YYYY-MM-DD`, weekly (day-of-week set) → `YYYY-Www`,
monthly (day-of-month set) → `YYYY-MM`, anything else → `YYYYMMDDTHHMM`.

The high-water mark is a `created|reused <task-ref> for <period>` line tagged
`recurring/<name>` in the repo-global `coga/log.md` — one writer and one parser
(`format_serviced_log`, `parse_serviced_period_entries`), pinned by a test. It
is not in the template blackboard, where any run rewriting a region could erase
it and re-fire the period. The line is append-only, union-merged, outlives the
reaped task, and is never composed into prompts.

Records are validated for exact shape and calendar values and compared by
calendar position. A malformed record is a template error in the sweep,
`coga recurring list` and `coga status`, never "ran this period". A period at
or below the newest valid record is not re-created or re-launched.
`read_serviced_ledger` reads the log **backwards** and stops once every
requested ref has a valid record at or after its target period; because
`merge=union` can put a newer record above an older one, an older hit never
stops the read. The first scan of a new period therefore walks the whole log;
later scans resolve from the tail. Malformed history older than the stop point
is allowed to heal. Freshness against control at publication is in
[recurring-admission](../../internals/recurring-admission/SKILL.md).

Current period only: missed periods are not chased, so a monthly run of a
weekly template produces one run.

## What a sweep does per template

One stable task per template (`recurring.create_template`):

- **Live** (`active`, or orphaned `in_progress` from a dead supervisor) — resumed
  from its frozen period ticket; no duplicate. A stuck run defers new periods.
- **Current-period `done`** and **`paused`** — skipped. A paused run is never
  replaced because another period is due.
- **Prior-period `done`** (not reaped by Dream) — deleted, then a fresh `active`
  task is created at step 1 with a new blackboard, state snapshot and ledger
  record. The delete runs only after proving the replacement can be created
  (workflow and step skills resolve); otherwise it is one template error and the
  old task stays.
- **`canceled`** — terminal; see `--force`. Delete it to run again.

**Launch order is phased**: orphan resumes, then fresh launches, each
most-overdue first — and the cleanup template, Dream, always **last**
(`_order_for_launch`), even as an orphan, so its retro pass sees the period
tasks this sweep just finished. Launches are sequential. The sweep prints a scan
table before launching.

## Variants

- `--force` runs every template regardless of schedule and status, reactivating
  `done` and `paused` periods — real Slack, sync and ledger advance. A `canceled`
  period gets a controlled refusal; the sweep continues and exits non-zero.
  Force does not bypass branch, owner or TTY gates.
- `coga recurring launch <name>` creates or reuses one template's task ignoring
  schedule and dedup (an explicit override when the period's task was reaped); a
  live run is resumed, a prior-period `done` replaced, a current-period `done` or
  any `paused` run left alone. It passes the sweep's concrete idle/max-session
  limits unless `--interactive`.
- `--interactive` needs an attended TTY, uses attended conduct and leaves the
  liveness limits unarmed. Every other automatic launch composes the recurring
  queue conduct (`prompt-queue.md`; see
  [session-conduct](../../session-conduct/SKILL.md)) and arms the idle timeout:
  `COGA_REPL_IDLE_TIMEOUT` > `[launch].idle_timeout` > 900 s (`0` or non-finite
  disarms); `COGA_REPL_MAX_SESSION` / `[launch].max_session` caps wall clock.
- `--agent <type>` is an ephemeral override for every agent-backed period in the
  sweep; `ticket.py` periods keep their deterministic path.
- `--all <path>` discovers Coga workspaces below an explicit path (skipping
  dependency/tool trees, `_` trees and Coga temp-control parents), omits
  unconfigured checkouts by count, runs one checkout per remote workspace in a
  fresh process, sequentially, and exits non-zero naming failed repos. Owner
  mismatches are skipped and named. Entry gates and off-branch service are in
  [recurring-control](../../internals/recurring-control/SKILL.md) and
  [recurring-temp-worktrees](../../internals/recurring-temp-worktrees/SKILL.md).

Every launching entry point runs from the control branch and honors the
committed `owner = "<name>"` gate: a policy gate against two operators racing,
not a lock, with no override flag. `coga recurring list` and `promote` are
ungated.

## Admission and unfinished runs

Agent-backed periods (including `delegate:`) need stdin and stdout TTYs; a
headless sweep skips them with a warning, before creating a period or leaving a
materialized one untouched, and continues. A `ticket.py` period runs headless
and is the shape for unattended schedulers.

A scheduled agent run must reach `done` in one launch. When an agent launch
returns unfinished — including a human/unassigned handoff or a `coga block` —
the sweep pauses it before continuing. Paused periods are not reminded by
`blocker-reminders`, so keep human gates and expected blockers out of scheduled
workflows. A **watchdog** pause (latest pause audit actor `system:watchdog`, not
superseded by a later human pause or creation) stays an unresolved failure:
every sweep shows `needs attention (watchdog timeout)` with the resume command,
counts it in `problems:`, notifies, and exits non-zero after other work. Resume
with `coga launch recurring/<name>` or `coga mark active recurring/<name>`.

## Failures and exit code

One template's failure never cancels the rest: the sweep records it, runs every
later due template, names all failures, and exits with the first failing code.
Two exits stop immediately: **75** (`git.RETRY_WITHOUT_SWEEP_EXIT_CODE`,
retained assist state needing reconciliation) and **≥ 128** (interrupt). Whatever
stops the loop, `recurring_runner._record_abandoned_due` names the stopping task
and each due task "admitted as due but never launched" in `problems:`. Absence
is a failure: an admitted watchdog recovery or a created period with no launch
outcome makes the sweep exit 2, except `skip (already handled on control)`.
A create sync to control that fails is non-fatal for the task — the created
period still launches — but it is named in `problems:` and exits 2. If the
created ticket then changed under that failed sync, the scan prints
`error (…)` for the template instead of any skip, and it never launches;
`--force` keeps the ordinary admission skip.
The [autofix](../autofix/SKILL.md) loop runs afterwards without changing the code.
