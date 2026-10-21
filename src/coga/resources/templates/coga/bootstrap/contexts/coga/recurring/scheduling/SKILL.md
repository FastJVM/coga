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

## Repo scope and clone scope

A template is `scope: repo` (the default) or `scope: clone`. Everything below
the next heading describes repo scope: one shared period task per firing,
serviced by whichever clone sweeps first and recorded in `coga/log.md`. That
is right for shared state and wrong for clone- or machine-local state, which
no other clone can see.

A `scope: clone` template is serviced once per period **in every clone that
sweeps** (`recurring_clone`, `recurring.scan_clone_due`). It requires a
reserved `ticket.py` and rejects `delegate`, `state_keys` and `workflow`.
The sweep runs the script directly, after the shared launches. No period task
is created, the runner commits nothing, and no log line is written.
A script's own state changes and publication belong to its template. The script gets
the template's `secrets` and `COGA_RECURRING_SCOPE=clone`,
`COGA_RECURRING_TEMPLATE` and `COGA_RECURRING_PERIOD`, but no `COGA_TASK_*`
variables, so there is nothing to bump. Exit 0 records the period in
`<primary checkout's coga dir>/.coga/recurring-clone/<name>.json`. That
directory is resolved through git's common dir, so a run from a temporary
control worktree counts for the clone that owns it. Any other exit is a sweep
failure, recorded for autofix and retried by the next sweep. The output is
kept beside the ledger in `<name>.log`. The owner, control-branch and
inactivity gates apply as for repo scope. `--force` and
`coga recurring launch <name>` ignore the clone ledger. `coga recurring
list` shows only this clone's state.

Clone scripts have a 15-minute wall-clock deadline (`run_clone_template`'s
`timeout`, independent of the agent REPL watchdog). Output is drained as it
arrives through a bounded buffer; the console and local log retain at most
the first 1,000,000 characters, with an explicit truncation marker. A truncated
log also keeps the last 4,000 characters; that tail is what the sweep's run
record receives. Timeout returns exit 124 with a diagnostic, terminates the
process group (the process tree on Windows), reaps the script, and leaves the
ledger unchanged so later templates can run and the next sweep can retry.
On Windows, a wrapper joins a supervisor-owned job object before starting the
script, so descendants remain owned after their parent exits. Job termination
and kill-on-close clean up the entire tree; setup or cleanup errors are reported,
never replaced by best-effort PID lookup. This adds one wrapper process on Windows.
The limit can interrupt legitimate long maintenance work, and truncation loses
middle output; increase the explicit runner limit when a job requires it.

Tradeoff, accepted: clone-scoped runs leave no runner-owned git-visible record.
Their evidence is the clone-local ledger and log, the console, and the autofix
run record.

An install older than clone scope fails silently rather than loudly: it
ignores the `scope` key it does not know and services a `scope: clone`
template as an ordinary shared period task, with a log line and no clone
ledger. This happens when the CLI lags the templates it sweeps, for example an
editable install whose source checkout sits behind `main`. The shipped clone
scripts tolerate it: with `COGA_TASK_SLUG` set they bump that task, so the
period closes instead of stalling. When a sweep creates a shared task for a
template already declaring clone scope, check the CLI version and editable
source checkout that created it. Upgrading an install that predates clone
scope resolves this mismatch ([coga/install](../../install/SKILL.md)).

The shipped `branch-sweep` template uses clone scope for local refs and
worktrees; its [ticket](https://github.com/FastJVM/coga/blob/main/coga/recurring/branch-sweep/ticket.md)
owns cleanup and worklist publication. `autoclose-merged` stays repo-scoped
because ticket closure is shared state. This repo's `upstream-coga` is
clone-scoped because it reads machine-local checkouts.

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
  fresh process, sequentially, and exits non-zero naming failed repos. Every
  other checkout of the same remote workspace gets a `--clone-only` child
  (`coga run recurring-scan --clone-only`), which runs only clone-scoped
  templates. Owner
  mismatches are skipped and named. Each child refreshes control before
  reading templates or periods; stale or diverged control refuses service.
  Off-branch children use a temporary control worktree without switching or
  stashing the operator's checkout.

Every launching entry point runs from the control branch and honors the
committed `owner = "<name>"` gate: a policy gate against two operators racing,
not a lock, with no override flag. `coga recurring list` and `promote` are
ungated.

A single-repo sweep or named launch started off control relays to an existing
control worktree of the same repo. If none exists, it refuses and names the
required control checkout. Direct `coga launch recurring/<name>` does not
relay. `--force` never bypasses the control-branch gate. Repos with Git sync
disabled or confirmed to be outside Git have no managed control checkout and
are exempt; a Git inspection failure is a refusal. Optional
[control implementation](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-control/SKILL.md)
and [temporary-worktree details](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-temp-worktrees/SKILL.md)
explain the machinery.
