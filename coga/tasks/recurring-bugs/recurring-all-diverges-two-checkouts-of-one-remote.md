---
slug: recurring-bugs/recurring-all-diverges-two-checkouts-of-one-remote
title: recurring --all diverges two checkouts of one remote
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
---

## Description

`coga recurring --all <path>` walks every coga repo under a path. When two of
those repos are **two working checkouts of the same git remote** (here
`~/Code/codex/coga` and `~/Code/claude/coga` both track `FastJVM/coga`), both
service the same recurring periods and both commit `Ticket:` / `Sync coga
state` bookkeeping to their own `main`. The two mains then diverge, and their
overlapping ticket-state edits genuinely conflict.

Observed 2026-07-17: after the sweep, `codex/coga` sat at
`main...origin/main [ahead 14, behind 14]`, with a content conflict on
`coga/tasks/validate-tickets-at-create-time.md` (one checkout marked it
`done` + PR #592, the other left it `blocked, step 3`). Every subsequent
`coga bump` / `mark` / sync spammed:

```
[git] sync failed: could not rebase 'main' onto origin/main: Rebasing (1/N)
CONFLICT (content): Merge conflict in coga/tasks/validate-tickets-at-create-time.md
```

The pre-scan catch-up (`_sync_control_checkout_ahead`) is best-effort and
silently skips on rebase conflict, so the scan proceeded on stale state and
the divergence widened. The `last_serviced_period` dedup prevents duplicate
*task rows*, but does **not** prevent two mains from diverging when both
checkouts commit ticket-state between fetches. During manual reconciliation
the remote advanced twice mid-push (`4a9daf50 -> 89999fce -> b9c38bd7`),
confirming a live push race between the checkouts.

**Fix direction — decide between (or combine):**
1. **Refuse-to-service on unconfirmed freshness:** if the pre-scan
   fetch/rebase can't confirm the checkout is at origin's tip (conflict,
   detached HEAD, `[git].enabled=false`), skip servicing this repo's period
   and report loudly, rather than proceeding on stale state — per repo,
   non-fatal to the rest of the `--all` sweep.
2. **Detect same-remote checkouts in `--all`:** when discovery finds two
   repos with the same resolved `origin` URL, service only one and warn about
   the rest, so one remote isn't raced by N checkouts.
3. Make `_sync_control_checkout_ahead`'s skip **visible** (it already prints a
   note; escalate to a per-repo warning in the sweep summary).

Needs a design call on which of these is the real fix; likely (1) as the
safety floor plus (2) as the ergonomic fix. Add an end-to-end test: two
clones of one remote service the same period; assert exactly one run and no
divergent push.

## Context

- Discovery + per-repo dispatch: `src/coga/recurring_runner.py`
  (`discover_coga_repos`, `run_recurring_all_repos`,
  `_sync_control_checkout_ahead`).
- Create/write reconcile seam: `_sync_recurring_create` /
  `_land_recurring_create_on_control_branch`, and `src/coga/git.py`
  (`sync_task_state` / `sync_paths` / `_land_paths_on_control_branch`).
- Existing regression that pins the single-checkout race:
  `tests/test_recurring.py::test_recurring_launch_removes_checked_out_control_task_when_race_handled`
  — drives `_sync_recurring_create` directly, NOT end-to-end through
  `run_recurring_all_repos` with two real checkouts. That end-to-end gap is
  the honest hole this ticket closes.
- Design note in `coga/architecture`: the launch-entry push gate is fatal but
  mid-workflow ticket-state sync is intentionally non-fatal (markdown is
  source of truth) — the fix must preserve that, not turn every sync miss
  fatal.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/595
branch: fix/recurring-remote-dedup
worktree: /tmp/coga-recurring-remote-dedup
commit: f5d63c90 peer-review: apply review findings (tip); ef7b2f06 implementation
freshness: rebased cleanly onto fetched origin/main ff5419d8

## Design decision

Use both defenses from the ticket: require the pre-scan control checkout catch-up
to confirm that the fetched control tip is integrated before servicing any
recurring period, and group `--all` discoveries by resolved configured remote so
only one checkout per remote workspace is dispatched. Distinct Coga workspaces
inside one monorepo remain independent scheduler targets, and a locally
configured control checkout wins when duplicate clones are otherwise eligible.
Freshness failure remains isolated to that repo; later task-state sync remains
non-fatal because markdown stays the source of truth.

## Implementation

- `run_recurring_all_repos` now groups git-enabled checkouts by resolved remote
  plus repo-relative Coga workspace path, prefers a locally configured control
  checkout, and names/skips every true duplicate without making that skip a
  sweep failure.
- Config errors during the grouping pre-pass are left for each repo's child
  process to report, preserving the parent sweep's per-repo failure isolation.
- The selected child receives a private freshness marker. Its pre-scan fetch,
  rebase, ancestry check, and unresolved-conflict check must succeed before
  `scan_due`; disabled git, detached/wrong branch, or catch-up failure exits
  nonzero for that repo while the parent continues.
- Bare single-repo and named recurring runs retain their prior best-effort
  catch-up, and post-entry task-state sync remains non-fatal.
- Updated the live and packaged architecture/sync contracts, packaged CLI
  reference, recurring bootstrap contract, and current-direction context.

## Verification

- Regression was observed red before the fix: both real clones were dispatched.
- `tests/test_recurring.py`: 120 passed.
- Full suite after peer-review fixes and again after the final rebase: 1314
  passed, 1 skipped.
- `coga validate --task recurring-bugs/recurring-all-diverges-two-checkouts-of-one-remote --json`:
  1 ok, 0 issues.
- The live `codex/coga` and `claude/coga` checkouts resolve as one duplicate
  group despite one remote URL carrying a trailing slash.

## Peer review

- Native `codex review --base main` reproduced three must-fix selection/isolation
  gaps: remote-only grouping collapsed distinct Coga workspaces in one
  monorepo; malformed config could abort the parent before later repos ran; and
  a no-user clone could shadow an equivalent configured clone.
- The follow-up groups by remote plus repo-relative workspace identity, keeps
  config discovery best-effort in the parent, and prefers a locally configured
  checkout already on its control branch.
- Focused regression matrix: 5 passed. Full `tests/test_recurring.py`: 120
  passed.

## PR

### Summary

- Deduplicate `coga recurring --all` by resolved remote workspace so duplicate
  clones cannot race one control branch, while distinct monorepo workspaces
  still run.
- Require every selected `--all` child to confirm control-branch freshness
  before scanning, without changing non-fatal task-state sync after entry.
- Preserve per-repo failure isolation and prefer a runnable configured control
  checkout when equivalent clones are discovered.

Test plan: `PYTHONPATH=$PWD/src python3.12 -m pytest -q` (1314 passed, 1 skipped) and task-scoped `coga validate --json`.
