---
slug: make-recurring-all-a-real-full-run-drop-the-debug
title: make recurring --all a real full run, drop the debug-sandbox machinery
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/cli
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
---

## Description

`relay recurring --all` is currently built as a "debug sandbox": it spins up
throwaway `<template>-dbg-<timestamp>` scratch task dirs, suppresses git
sync and Slack notifications by detecting the `-dbg-` slug, auto-reaps
orphaned scratch dirs, and folds each run's outcome back into the template
`log.md`. That sandbox framing was a **misunderstanding** — `--all` was only
ever meant to **force a real, full run of every recurring template, ignoring
the schedule and the status filter**. Nothing more.

Worse, the sandbox is a leaky half-measure: isolation is enforced by the task
*slug* (`is_debug_slug`), but workers that reach a fixed global path bypass it
entirely. Concretely, a `--all` sweep on 2026-06-18 **posted a real digest to
Slack and drained the real production spool**, because `run_digest` resolves
`digest_spool_path(cfg)` → the real `recurring/digest/` dir and calls
`post(cfg, message, task_path=spool_path.parent)`, neither of which is gated
by `is_debug_slug`. Dream's debug child tasks (`dream-debug-validate-drift`,
etc.) also leaked into the spool because their slugs carry no `-dbg-` infix.

So the run is neither hermetic nor honestly real — the worst of both. Fix the
contradiction by deleting the sandbox concept: make `--all` behave **exactly
like a normal `relay recurring`** except that it bypasses the schedule and the
done/paused/in_progress status filter and runs **every** template.

### Desired behavior

- `relay recurring --all` force-runs every template under `relay-os/recurring/`
  for real: real Slack, real spool drain, real git task-state sync, real
  `last_serviced_period` advance — identical to a normal run, just forced.
- The only difference from a bare `relay recurring` is: ignore the schedule,
  and ignore the status filter that skips already-serviced / done / paused
  templates this period. A template that already ran this period is still
  re-run (force).
- No `-dbg-` scratch dirs, no slug-based suppression, no orphan reaping, no
  fold-back-to-template-log step.

### Open sub-decision for the implementer

"Force a real full run" must actually *execute* every template even when this
period's real `recurring/<name>` task is already `done`. Two coherent ways:

1. **Reuse the real period task and force-relaunch it.** `relay launch` on a
   `done` ticket already re-activates and restarts the workflow at step 1, so
   `--all` can get-or-create the real `recurring/<name>` task and force-launch
   each, with no scratch dirs at all. Preferred — simplest, fully real, reuses
   existing launch semantics.
2. Spin fresh real (non-`-dbg-`) task instances per template. Heavier; only if
   reusing the real dir causes a problem (e.g. clobbering an in-flight run).

Go with (1) unless implementation surfaces a concrete blocker; note the choice
on the blackboard.

### Scope / files (starting points, verify during implement)

- `src/relay/commands/recurring.py` — remove the debug-scratch launch path,
  `_finalize_debug_run`, `_read_debug_outcome`, `_reap_debug_orphans`, and the
  `-dbg-` slug minting; rewrite `--all` as force-run-every-template.
- `src/relay/recurring.py` — `is_debug_slug` and any debug-slug helpers, if no
  longer referenced after the above.
- `src/relay/git.py:~98-110` — drop the `is_debug_slug` git-sync suppression.
- `src/relay/notification/__init__.py:~119-130` — drop the `is_debug_slug`
  Slack/spool suppression.
- `tests/` — update/remove tests asserting the sandbox behavior; add a test
  that `--all` force-runs an already-`done`/not-due template for real.
- Docs/contexts must move in the same PR (CLAUDE.md rule): the `relay/cli`
  context's `relay recurring --all` paragraph and the `relay/architecture`
  recurring section both currently describe the disposable-scratch behavior —
  rewrite them to "forces a real full run of every template." Keep the live
  `relay-os/` copy and the packaged `src/relay/resources/templates/relay-os/`
  copy in sync.

### Verification

- `python -m pytest` green.
- Manually: `relay recurring --all` on this repo runs every template as a real
  run (real Slack post for digest, real spool drain, real `last_serviced_period`
  bump), creates no `*-dbg-*` dirs, and leaves no leftover scratch.

## Context

The 2026-06-18 sweep left these uncommitted artifacts as evidence of the leak:
`recurring/{autoclose-merged,digest,dream,skill-update}/log.md` fold-back lines
and a rewritten `recurring/digest/blackboard.md` (`posted: yes`, spool drained).
These can be discarded with `git checkout -- relay-os/recurring/` independent of
this ticket.

See `relay/architecture` (recurring primitive + the `--all` description) and
`relay/cli` (`relay recurring --all`) for the behavior being changed.

<!-- relay:blackboard -->

# make-recurring-all-a-real-full-run-drop-the-debug

## Dev
branch: drop-debug-all
worktree: ../relay-drop-debug-all
pr: https://github.com/FastJVM/relay/pull/411

## Open PR — DONE
- Pushed `drop-debug-all`, opened PR #411 against `main`.
- Auth verified (`gh auth status` OK, https remote).
- No CI configured on this repo (`gh pr checks` reports none) — nothing to gate on.


## Goal
Delete the `--all` debug-sandbox machinery. Make `relay recurring --all` behave
exactly like a bare `relay recurring`, except it bypasses (a) the schedule and
(b) the status filter that skips already-serviced/done/paused templates this
period. Every template gets force-run as a REAL run (real Slack, real spool
drain, real git task-state sync, real `last_serviced_period` advance).

## Design decision — sub-decision in ticket
Going with **option 1** (preferred): reuse the real `recurring/<name>` period
task and force-relaunch it. No scratch dirs. `relay launch` already re-activates
a `done`/`paused` ticket (restarts workflow at step 1), so `--all` just needs to
get-or-create the real task and launch every one regardless of status.

Implementation: thread a `force` flag into `scan_due` that skips the
"period-already-serviced → ref=None" early-skip. Add `DueScan.forced` (every
materialized task with a ref, in launch order, Dream last) vs `DueScan.due`
(launchable only). `--all` launches `scan.forced`; everything else (broadcast,
git sync, idle backstops, `_stop_if_unfinished_after_launch`) is the SAME loop
as the bare sweep.

## Changes

### Production code
- `src/relay/recurring.py`
  - `scan_due(..., force=False)`: guard the ref=None skip with `not force`.
  - `DueScan.forced` property + shared `_order_for_launch` ordering.
  - DELETE: `is_debug_slug`, `_DEBUG_SLUG_RE`, `create_debug_run`, `scan_debug`.
    Update `__all__`.
- `src/relay/commands/recurring.py`
  - `main()`: drop `_reap_debug_orphans` call; unify `--all` into the normal
    launch loop (`scan_due(force=all_)`, launch `scan.forced if all_ else scan.due`).
  - DELETE: `_launch_all_debug`, `_read_debug_outcome`, `_finalize_debug_run`,
    `_reap_debug_orphans`, `_without_debug_log_entries`, `_debug_log_entries`,
    `_control_log_with_local_debug`. Simplify their call sites in the
    recurring-create git-sync helpers (debug log-line filtering is now dead;
    control log = `_show_path(...)`). Keep `_control_blackboard_with_local_period`
    (period high-water merge, not debug).
  - Drop now-unused imports (`is_debug_slug`, `scan_debug`, `tasks_dir`),
    rewrite `--all` help text + callback docstring.
- `src/relay/git.py`: drop the `is_debug_slug` sync suppression in `sync_task_state`.
- `src/relay/notification/__init__.py`: drop the `is_debug_slug` suppression in `notify`.
- `src/relay/mark.py`: drop both `is_debug_slug` checks (`_sync_done_state`,
  `_warn_if_state_not_advanced`).

### Tests
- DELETE: `test_is_debug_slug`, `test_reap_debug_orphans_removes_only_debug_dirs`,
  `test_scan_debug_creates_fresh_isolated_run`,
  `test_scan_debug_does_not_advance_period_high_water`,
  `test_recurring_launch_syncs_ledger_without_debug_log_entries` (test_recurring.py),
  `test_sync_suppressed_for_debug_run` (test_git.py),
  `test_notify_skips_debug_task_*` x2 (test_digest.py).
- REWRITE `test_recurring_all_launches_every_template`: assert `--all`
  force-launches the REAL `recurring/<name>` task (no `-dbg-`), no scratch left.
- ADD a test: `--all` force-runs a template whose real period task is already
  `done`/not-due (relaunches the real task for real).
- Fix imports in test_recurring.py (drop `is_debug_slug`, `scan_debug`).

### Docs/contexts (CLAUDE.md same-PR rule)
- `relay-os/bootstrap/contexts/relay/cli/SKILL.md` `--all` paragraph + the idle
  backstop line + pick-which-command line; mirror to packaged
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/cli/SKILL.md`.
- Local contexts that describe the scratch behavior (no packaged copy):
  `relay-os/contexts/relay/recurring/SKILL.md`,
  `relay-os/contexts/relay/current-direction/SKILL.md`, and `docs/design.md`.
- NOTE: `relay/architecture` context does NOT mention `--all`/scratch (grep
  confirms), so no architecture edit needed despite the ticket naming it.

## Verification — DONE (implement step)
- `python -m pytest` (run against worktree via `PYTHONPATH=<worktree>/src`):
  **798 passed, 1 skipped, 2 failed**. The 2 failures are
  `tests/test_autoclose_sweep.py::{test_autoclose_recurring_template_creates_idempotently,
  test_autoclose_live_and_packaged_copies_stay_in_sync}` and are **pre-existing
  on main HEAD** — committed drift in `relay-os/recurring/autoclose-merged/
  blackboard.md` (`last_serviced_period: 2026-06-17` present live, absent in the
  packaged copy). Unrelated to this change (verified by reproducing on the main
  checkout). Same `recurring/` leak the ticket flags as discardable.
- All tests in the files I touched (recurring/git/digest/mark) pass: 145 passed.
- Manual `relay recurring --all` smoke not yet run end-to-end (would post real
  Slack + drain spool on this repo); the CLI-level behavior is covered by
  `test_recurring_all_launches_every_template` (asserts it launches the real
  `recurring/<name>`, no `-dbg-` dir, no scratch-removal step).

## Implementation notes / decisions
- `--all` shares the bare-sweep launch loop: `scan_due(force=all_)` +
  `scan.forced if all_ else scan.due`. `force` only skips the
  period-already-serviced ref=None branch; `create_template` still get-or-creates
  the real `recurring/<name>` (reuses a `done`/`paused` one — relay launch
  re-activates). New `DueScan.forced` + shared `_order_for_launch` (Dream last).
- Dropped `is_debug_slug`/`_DEBUG_SLUG_RE`/`create_debug_run`/`scan_debug` and all
  4 slug-based suppression sites (git.py, notification, mark.py x2). The
  recurring-create git-sync log helpers had debug-line filtering that's now dead
  (no `-dbg-` lines ever written) → simplified `_control_log_with_local_debug`/
  `_without_debug_log_entries`/`_debug_log_entries` to `_control_log` (behavior
  preserved; the stale-ledger sync tests still pass).
- Docs: tracked source-of-truth edits only. The live `relay-os/bootstrap/` copy
  is gitignored AND materialized from a *newer installed package* than this
  repo's `src/` (it has `relay build`/`relay secret get` not in src), so I left
  it to `relay init --update` and edited the tracked packaged template
  (`src/relay/resources/.../bootstrap/contexts/relay/cli/SKILL.md`) plus the
  tracked local contexts (`relay/recurring`, `relay/current-direction`) and
  `docs/design.md`. Architecture context has no `--all`/scratch text → untouched.

## Net diff: ~ -433 lines (12 files).

## Pre-existing uncommitted artifacts (task context)
The dirty `relay-os/recurring/*/log.md` + `digest/blackboard.md` are leak
evidence; discard separately with `git checkout -- relay-os/recurring/`. Not
part of this branch.

## Peer Review — DONE (codex)
- Review command: `codex review --base main` from `/home/n/Code/relay-drop-debug-all`.
- Finding fixed: `--all` sorted forced launches using stale local status before
  reconciling existing task state with the control branch. In a stale checkout,
  a local `done` task whose control copy is `in_progress` could be ordered after
  fresh work and never resume if an earlier task stopped the sweep.
- Fix: scan-time `--all` reconciliation now refreshes existing task status
  read-only from the control branch before `scan.forced` sorts; actual task
  restore/sync still happens in `_prepare_forced_launch` only when that task is
  reached. Added
  `test_recurring_all_reconciles_existing_tasks_before_launch_order`.
- Commit: `d143f69 peer-review: apply review findings`.
- Verification:
  - `PYTHONPATH=src python -m pytest tests/test_recurring.py::test_recurring_all_restores_clean_stale_existing_task_from_control tests/test_recurring.py::test_recurring_all_snapshot_does_not_block_control_restore tests/test_recurring.py::test_recurring_all_reconciles_existing_tasks_before_launch_order -q -p no:cacheprovider` — 3 passed.
  - `PYTHONPATH=src python -m pytest tests/test_recurring.py tests/test_notification_messages.py tests/test_digest.py tests/test_git.py -q -p no:cacheprovider` — 140 passed.
  - `PYTHONPATH=src python -m pytest -q -p no:cacheprovider` — 809 passed, 1 skipped, 2 failed; the failures are the known pre-existing `tests/test_autoclose_sweep.py` live/package `autoclose-merged/blackboard.md` drift (`last_serviced_period: 2026-06-17` in live only).
