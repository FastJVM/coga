---
slug: auto/launch-should-refresh-local-coga-state-at-end-of-r
title: Launch should refresh local coga state at end of run
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
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
script: null
---

## Description

When a `coga launch` run ends (bump handoff, mark done, block, or agent exit),
the checkout the launch was run from should be refreshed so its `coga/` state
matches what the run just published to the control branch — the ticket that was
worked, `coga/log.md`, and any other `coga/tasks/**` state that landed on
`origin/<control>` during the run. Today the sync is publish-only:
`src/coga/git.py` lands task state on the control branch (and fast-forwards the
local control *ref* best-effort), but its own docs note that a checkout on any
other branch "stays stale after every launch until a manual pull". The operator
who just watched a launch finish then runs `coga status` in the same terminal
and sees a stale world — the completed step is missing or shown at an old step,
with no signal that the view is stale.

Scope:

- At the end of a launch run (all exit paths the supervisor sees), fetch
  `origin/<control>` and update the launch checkout's `coga/` subtree —
  `coga/tasks/**` and `coga/log.md` (union-merge for the log) — from it.
  Working-tree product files outside `coga/` are never touched.
- The refresh must be safe on a feature-branch checkout: it updates the
  `coga/` files (committing on the current branch the same way mid-run ticket
  sync already does), not the branch's source tree.
- Failure to refresh is non-fatal but loud (stderr + log), matching the
  existing mid-run sync-miss posture.
- Complementary, if cheap: `coga status` warns when the remote-tracking
  `origin/<control>` ref has newer `coga/tasks/**` than the checkout —
  comparing local refs only, no fetch, so status stays read-only/no-network.

## Context

Observed 2026-07-13: a launch running in a worktree bumped
`install/recommend-virtualenv-not-system-python` to step 4 and published the
state to `origin/main` correctly, but the operator's checkout (on a feature
branch) still showed the ticket at step 1/active and `coga status install`
rendered the stale table with no warning. Same root cause made the stuck
`install/document-where-to-run-init-and-adopt-existing-repo` open-pr failure
harder to spot. The publish half of the sync is verified working; this ticket
adds the missing pull-back half at the one place that already owns network
access and the run lifecycle — the launch supervisor.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/544
branch: launch-end-refresh
worktree: /home/n/Code/claude/coga-launch-end-refresh

## Plan (implement step)

Three pieces, all scoped to the ticket:

1. `git.refresh_coga_state_from_control(cfg, *, message)` in `src/coga/git.py` —
   the pull-back half. Fetch `origin/<control>`; on the control branch itself a
   plain `merge --ff-only FETCH_HEAD`; on a feature branch, overlay only
   `coga/tasks/**` files that differ between HEAD and the control tip into the
   working tree and commit them on the current branch (mirrors the mid-run
   feature-branch local commit), union-merging `coga/log.md` three-way so
   local-only log lines survive. Safety rails: skip paths dirty in the working
   tree (hand-edits belong to the sweep + regression guard, not a blind
   overwrite), and skip ticket files whose local state is *ahead* of control
   (reuses `_ticket_state_from_bytes` / `_ticket_state_regression_reason` with
   the roles swapped). Detached HEAD skips (commit would be orphaned). Failure
   model identical to `sync_paths`: GitError → stderr + log, never a crash.
2. Launch integration (`src/coga/commands/launch.py`): `_refresh_launch_checkout(base_cfg)`
   called once on every exit path — after the script-mode dispatch returns, in
   the setup `except BaseException` handler, and in the supervisor loop's
   `finally` (after worktree cleanup so the cleanup sweep's landing is included
   in what gets pulled back). Always against `base_cfg` (the checkout the
   operator ran `coga launch` from), never the isolation worktree cfg.
3. `coga status` staleness warning: `git.stale_coga_task_rels(cfg)` compares the
   local remote-tracking `refs/remotes/<remote>/<control>` tree against the
   working tree under `coga/tasks/**` — local refs only, zero network, fail-open
   to `[]` — counting only ticket files where the remote copy is strictly ahead
   (or exists remotely but not locally). `render_status` prints a yellow stderr
   warning when non-empty, keeping stdout parseable and the render read-only.

Also: update the `git.py` module docstring ("stays stale after every launch
until a manual pull" is no longer true), and stub the new refresh entry point in
tests/conftest.py `_stub_git` so non-git tests don't shell out.

## Implemented (step 1 done)

Commit `dfa6e5d5` on `launch-end-refresh` (based on current origin/main
56fa3281, rebase re-checked: up to date). 10 files, +686 lines, all additive.

- `src/coga/git.py`: `refresh_coga_state_from_control()` — fetch
  `origin/<control>`; control-branch checkout gets `merge --ff-only`; feature
  branch gets a scoped overlay of differing `coga/tasks/**` files committed on
  the current branch, `log.md` three-way union-merged. Guards: dirty paths
  skipped, locally-ahead tickets skipped (reuses the `_TicketState` regression
  helpers), detached HEAD skipped. GitError → stderr + log, never raises.
  Also `stale_coga_task_rels()` — the no-fetch status probe (remote-tracking
  ref vs working tree, ticket-state-ordered, fail-open to []). Module
  docstring gained a paragraph on the pull-back half.
- `src/coga/commands/launch.py`: `_refresh_launch_checkout(base_cfg)` called
  exactly once per exit path — inline after a clean script-mode dispatch, in
  the setup `except BaseException` handler (covers failed scripts + post-
  activate bails), and in the supervisor `finally` after worktree cleanup
  (cleanup's sweep lands leftovers first, so the refresh pulls them back too).
  Always `base_cfg`, never the isolation-worktree cfg.
- `src/coga/views.py`: `render_status` prints one yellow *stderr* warning when
  the probe reports newer remote ticket state (stdout stays parseable).
- Context: new "launch-end pull-back" section in `coga/contexts/coga/sync/
  SKILL.md`, mirrored byte-identical into the packaged copy under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`.
- Tests: conftest `_stub_git` stubs the two new entry points (incl. the
  views-bound name); 13 new real-git tests in `test_git.py` (pull-back,
  guards, union merge, ff path, detached, non-fatal fetch failure, probe
  semantics incl. never-fetches); launch-level once-per-exit-path tests in
  `test_launch.py` + `test_launch_script.py`; render warning test in
  `test_views.py`.

Verification: `python3.12 -m pytest` (PYTHONPATH=src, no venv on this box) —
**1187 passed, 1 skipped**; the only failure,
`test_bootstrap_script_launch_is_stateless`, fails identically on unmodified
origin/main (child process needs an *installed* coga; env artifact, not this
change). `test_usage_probe.py::test_codex_probe_primes_once_across_reads`
flaked once in a full-suite run and passes alone and on the rerun — unrelated.

Decisions worth reviewing:
- Refresh scope on a feature branch is exactly the ticket's: `coga/tasks/**` +
  union-merged `log.md`. Other `coga/` state (contexts, recurring, spool) is
  not pulled back — out of scope per ticket.
- On a control-branch checkout the refresh is a plain ff merge of the whole
  branch (that checkout *is* the control branch; equivalent to `git pull
  --ff-only`), and a diverged local control is a loud miss, not a merge.
- The BaseException-handler call means even a refused launch after
  auto-activate does a fetch; judged correct ("all exit paths") and cheap.

## Findings

- The publish half fast-forwards the local *control ref* only
  (`_try_update_local_ref`); a checkout on any other branch never sees the new
  state — matches the observed 2026-07-13 staleness.
- The CLI dispatch sweep (`cli._sweep_coga_state`) runs after `launch()` returns,
  so the refresh must commit what it writes; a clean tree afterwards makes the
  sweep a no-op.
- `status`/`show`/`validate` are non-sweeping read-only commands (principle 6),
  hence the no-fetch constraint on the status warning.

## Peer review

Review approved after one must-fix safety correction. The original feature-
branch overlay diffed whole branch tips, so a clean committed task edit that
existed only on the feature side could be mistaken for control-side freshness,
overwritten, and committed away. Commit `3cbc23aa` now limits candidates to
control-side changes since the merge base and overwrites committed divergence
only when control history proves it already absorbed that exact local version.
Real-git regressions cover same-step blackboard divergence, task attachments,
and the normal absorbed-then-advanced convergence path.

The branch was rebased onto `origin/main` at `5cc75ee3` and is clean with two
commits ahead. Final verification on the rebased history:
`PYTHONPATH=/home/n/Code/claude/coga-launch-end-refresh/src python3.12 -m pytest`
— **1191 passed, 1 skipped**.

## PR

### Summary

- Refresh the checkout that invoked `coga launch` from the control branch at
  every supervised exit, updating task state without touching product files.
- Union-merge `coga/log.md`, preserve dirty or unabsorbed committed local task
  state, and warn on stderr when `coga status` can prove its local view is stale
  from remote-tracking refs without fetching.
- Document the pull-back contract and cover feature/control branches, failure
  paths, launch teardown, and status rendering with real-git regressions.

### Test plan

`PYTHONPATH=/home/n/Code/claude/coga-launch-end-refresh/src python3.12 -m pytest` — 1191 passed, 1 skipped.

## Usage

{"agent":"claude","cache_creation_input_tokens":549387,"cache_read_input_tokens":22750847,"cli":"claude","input_tokens":265,"model":"claude-fable-5","output_tokens":233876,"provider":"anthropic","schema":1,"session_id":"5d36927f-c621-47ce-87d8-cef4696e409c","slug":"auto/launch-should-refresh-local-coga-state-at-end-of-r","step":"implement","title":"Launch should refresh local coga state at end of run","ts":"2026-07-14T03:39:22.312996Z","usage_status":"ok"}
