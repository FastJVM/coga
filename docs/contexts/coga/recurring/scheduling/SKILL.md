---
name: coga/recurring/scheduling
description: How a recurring sweep runs due work — per-template status handling, phased launch order, `--force`, named, interactive and `--all` launches, and the owner gate; period keys and the ledger, repo inactivity, and admission, unfinished runs and failures live in its leaves.
---

# Recurring scheduling and sweeps

## Leaves

- [coga/recurring/scheduling/ledger](ledger/SKILL.md) — period keys and the
  serviced-period ledger.
- [coga/recurring/scheduling/inactivity](inactivity/SKILL.md) — the
  repo-inactivity gate and `run_when_inactive`.
- [coga/recurring/scheduling/failures](failures/SKILL.md) — TTY admission,
  unfinished and watchdog-paused runs, failures and the sweep's exit code.

## What a sweep does per template

The shipped daily `autoclose-merged` template runs the registered `autoclose`
recipe, then `branch-sweep`, then bumps its period task. The branch pass runs
even when no ticket closed; either recipe's non-zero exit stops the sequence
before bump and records the failure on the period blackboard. Branch outcomes
appear there under `## Branch Sweep`. Direct `coga run autoclose` retains its
ticket/worklist scope; the daily composition lives in the template's `ticket.py`.

This deliberately replaces the daily-recorded/weekly-unrecorded cleanup split:
unclaimed landed branches are checked daily at the cost of extra GitHub API
calls. The standalone Monday `branch-sweep` schedule remains an independent
retry and manual entry point. Both use the existing
[checkout cleanup proofs](../../../dev/checkout-cleanup/proofs/SKILL.md); daily
frequency grants no new deletion authority. That includes the
[terminal-owner rule](../../../dev/checkout-cleanup/terminal-owners/SKILL.md):
a branch whose PR closed unmerged is released only when a done or canceled
ticket owns it. The daily pass is the integration point for terminal
transitions, which delete nothing themselves; a refusal is reported under
`## Branch Sweep` and retried the next day.

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
