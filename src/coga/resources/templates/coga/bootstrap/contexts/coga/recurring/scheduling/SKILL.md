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
anything else → `YYYYMMDDTHHMM`.

The high-water mark is a `created|reused <task-ref> for <period>` line tagged
`recurring/<name>` in the repo-global `coga/log.md`. It is not in the template
blackboard, where a run rewriting a region could erase it and re-fire the
period. The line is append-only, outlives the reaped period task, and is never
composed into prompts. A period at or below the newest valid record is not
re-created or re-launched. A malformed record is a template error in the
sweep, `coga recurring list` and `coga status`, never "ran this period".

Current period only: missed periods are not chased, so a monthly run of a
weekly template produces one run. A new template's first sweep services the
most recent past firing ([templates](../templates/SKILL.md#first-firing-is-retroactive)).

## Repo scope and clone scope

A template is `scope: repo` (the default) or `scope: clone`. Repo scope is one
shared period task per firing, serviced by whichever clone sweeps first and
recorded in the ledger above. That is right for shared state and wrong for
clone- or machine-local state, which no other clone can see.

A `scope: clone` template is serviced once per period **in every clone that
sweeps**. It requires a reserved `ticket.py` and rejects `delegate`,
`state_keys` and `workflow`. The sweep runs the script directly, after the
shared launches. No period task is created, the runner commits nothing, and no
log line is written; a script's own state changes and publication belong to
its template. The script gets the template's `secrets` and
`COGA_RECURRING_SCOPE=clone`, `COGA_RECURRING_TEMPLATE` and
`COGA_RECURRING_PERIOD`, but no `COGA_TASK_*` variables, so there is nothing to
bump. Exit 0 records the period in `<primary checkout's coga
dir>/.coga/recurring-clone/<name>.json`, with the output beside it in
`<name>.log`; a run from a temporary control worktree counts for the clone that
owns it. Any other exit is a sweep failure, recorded for autofix and retried by
the next sweep. The owner, control-branch and inactivity gates apply as for
repo scope. `--force` and `coga recurring launch <name>` ignore the clone
ledger. `coga recurring list` shows only this clone's state.

Clone scripts have bounded runtime and output. A timeout reports the failure,
terminates the script's process tree and leaves the period retryable, so later
templates still run. Truncated console output points to the local log for the
final output; the run record also receives that tail. Implementation limits
are in [recurring-clone](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-clone/SKILL.md).

Clone-scoped runs leave no runner-owned git-visible record. Their evidence is
the clone-local ledger and log, the console, and the autofix run record. The
shipped `branch-sweep` template uses clone scope for local refs and worktrees;
its [ticket](https://github.com/FastJVM/coga/blob/main/coga/recurring/branch-sweep/ticket.md)
owns cleanup and worklist publication. `autoclose-merged` stays repo-scoped
because ticket closure is shared state. A `scope: clone` template serviced as a
shared period task means the CLI predates clone scope
([coga/install](../../install/SKILL.md#cli-older-than-the-templates-it-sweeps)).

## What a sweep does per template

One stable task per template:

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
most-overdue first — and the cleanup template, Dream, always **last**, even as
an orphan, so its retro pass sees the period tasks this sweep just finished.
Launches are sequential. The sweep prints a scan table before launching.

## Variants

This section owns the recurring command spellings' behavior; flags and syntax
are `coga recurring --help`'s. The bare, forced and `--all` sweeps run the fixed
`recurring-scan` recipe through `coga run`.

- `--force` runs every template regardless of schedule and status, reactivating
  `done` and `paused` periods — real Slack, sync and ledger advance. A `canceled`
  period gets a controlled refusal; the sweep continues and exits non-zero.
  Force does not bypass branch, owner or TTY gates.
- `coga recurring launch <name>` (and default aliases such as `coga dream`)
  creates or reuses one template's task ignoring schedule and dedup (an explicit
  override when the period's task was reaped); a live run is resumed, a
  prior-period `done` replaced, a current-period `done` or any `paused` run
  left alone. It passes the sweep's concrete idle/max-session limits unless
  `--interactive`.
- `--interactive` needs an attended TTY, uses attended conduct and leaves the
  liveness limits unarmed. Every other automatic launch composes the recurring
  queue conduct (`prompt-queue.md`; see
  [prompt composition](../../prompt-composition/SKILL.md#session-conduct)) and arms the idle timeout:
  `COGA_REPL_IDLE_TIMEOUT` > `[launch].idle_timeout` > 900 s (`0` or non-finite
  disarms); `COGA_REPL_MAX_SESSION` / `[launch].max_session` caps wall clock.
- `--agent <type>` is an ephemeral override for every agent-backed period in the
  sweep; `ticket.py` periods keep their deterministic path.
- `--all <path>` discovers Coga workspaces below an explicit path (skipping
  dependency/tool trees, `_` trees and Coga temp-control parents), omits
  unconfigured checkouts by count, runs one checkout per remote workspace in a
  fresh process, sequentially, and exits non-zero naming failed repos. Every
  other checkout of the same remote workspace gets a `--clone-only` child,
  which runs only clone-scoped templates. Owner mismatches are skipped and
  named. Each child refreshes control before reading templates or periods;
  stale or diverged control refuses service. Off-branch children use a
  temporary control worktree without switching or stashing the operator's
  checkout.
- `coga recurring list` is read-only: templates, firings, period state.
  `coga recurring promote` is in [templates](../templates/SKILL.md#promotion).

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

## Admission and unfinished runs

Agent-backed periods (including `delegate:`) need stdin and stdout TTYs; a
headless sweep skips them with a warning, before creating a period or leaving a
materialized one untouched, and continues. The skipped template keeps its scan
row, `skip (agent needs a TTY)`, rather than a `## Template errors` entry; this
headless skip is not counted in `problems:`. A current period that is not
launchable (`canceled`, `blocked`, ...) is never refused: a durable checkout
would not launch it either. A `ticket.py` period runs headless and is the shape
for unattended schedulers.

A scheduled agent run must reach `done` in one launch. When an agent launch
returns unfinished — including a human/unassigned handoff or a `coga block` —
the sweep pauses it before continuing. The blocker-reminder job keeps open
asks on paused periods visible under its
[eligibility and deduplication contract](https://github.com/FastJVM/coga/blob/main/coga/recurring/blocker-reminders/ticket.md);
it does not resume them. Keep human gates and expected blockers out of scheduled
workflows. A **watchdog** pause (latest pause audit actor `system:watchdog`, not
superseded by a later human pause or creation) stays an unresolved failure:
every sweep that admits the template through the inactivity gate shows
`needs attention (watchdog timeout)` with the resume command, counts it in
`problems:`, notifies, and exits non-zero after other work. Resume with
`coga launch recurring/<name>` or `coga mark active recurring/<name>`.

## Failures and exit code

One template's failure never cancels the rest: the sweep records it, runs every
later due template, names all failures, and exits with the first failing code.
A template that cannot be scanned (`## Template errors`: unloadable, bad ledger
record, failed create) is named on stderr, in the Slack alert, and in
`problems:`; on its own it does not change the exit code. A sweep with any
refused or errored template never reports "No recurring tasks due".
Two exits stop immediately: **75** (retained assist state needing
reconciliation) and **≥ 128** (interrupt). Whatever stops the loop, the
stopping task and each due task "admitted as due but never launched" are named
in `problems:`.

Absence is a failure: an admitted watchdog recovery or a created period with no
launch outcome makes the sweep exit 2, except `skip (already handled on
control)`. A create sync to control that fails is non-fatal for the task — the
created period still launches — but it is named in `problems:` and exits 2. If
the created ticket then changed under that failed sync, the scan prints
`error (…)` for the template instead of any skip, and it never launches;
`--force` keeps the ordinary admission skip. A period adopted from control
stays `skip (already handled on control)` even when publishing its log line
fails; that failure is still named in `problems:`. All of this is the sweep
path. The [autofix](../autofix/SKILL.md) loop runs afterwards without changing
the exit code.
