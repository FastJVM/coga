---
slug: recurring-bugs/branch-sweep-leaves-worktree-pinned-merged-branche
title: Branch-sweep leaves worktree-pinned merged branches behind
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/architecture
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
step: 4 (review)
---

## Description

`branch-sweep` silently fails to delete a merged branch that any git worktree
still holds — including a **prunable** worktree whose directory is already
gone. The sweep exits 0 and the branch survives, so every week
`rebase-stale-worktrees` re-enumerates it, re-conflicts on it, and reports it
again as residue branch-sweep should have removed.

### The mechanism

`src/coga/branchsweep.py` never mentions worktrees — the word does not appear
in its 301 lines. For a squash-merged branch (tip not an ancestor of the
control branch) the delete path reaches `branchcleanup.py:199`:

```python
forced = _git(root, "branch", "-D", branch)
```

Git refuses that whenever a worktree holds the branch:

```
error: cannot delete branch 'x' used by worktree at '<path>'
```

`branchcleanup.py:210-211` catches the non-zero exit, notes
`could not delete local 'x': <stderr>`, and the caller
(`branchsweep.py:126-127`) files it under the generic `skipped` list. Nothing
distinguishes "left alone deliberately" from "git refused and we gave up", so
the failure never rises above routine skip noise.

A worktree whose directory has been deleted still pins its branch until
`git worktree prune` runs, so branches accumulate as `/tmp` worktrees are
cleared by reboots.

### Verified, not assumed

Probe run 2026-07-27 in this repo: created a scratch branch, added a worktree
for it, deleted the worktree directory, then attempted the delete. Git
refused with the error above (exit 1) even though the directory was gone.
`git worktree prune` cleared the record and the same delete then succeeded.

At the time of the probe this repo had 27 worktrees, **18 of them prunable**,
each pinning a branch invisibly to branch-sweep.

## Proposed fix

1. `git worktree prune` before the delete pass, so worktrees whose directories
   are already gone stop pinning branches.
2. For a merged branch still held by a **live** worktree, decide deliberately
   rather than falling through to a generic skip — either `git worktree
   remove` it or report it under its own outcome.
3. Give it a distinct outcome name (e.g. `skipped-worktree-pinned`) separate
   from the generic `skipped` bucket, so the condition is legible in the run
   output instead of buried.

Point 3 is the fail-loud half and matters most: this ran for weeks precisely
because a refused delete was indistinguishable from an intentional skip
(principle 6).

## Context

- `src/coga/branchsweep.py` — `sweep_branches`, the `skipped` bucket at
  lines 126-127.
- `src/coga/branchcleanup.py` — `delete_local_branch`, the `-D` call at
  line 199 and the swallowed failure at lines 210-211.
- The counterpart recurring task is `coga/recurring/rebase-stale-worktrees/`,
  whose W31 run summary reported 16 of 17 stale branches as merged residue and
  closed with: *"If branch-sweep is not deleting merged branches that still
  have worktrees, fixing that is worth more than another sweep here."*
- Tests live in `tests/test_branchsweep.py` / `tests/test_branchcleanup.py`;
  a regression test wants a worktree-pinned merged branch fixture.

### Not part of this ticket

Ordering. The W31 rebase summary was already stale when written — branch-sweep
ran seven minutes after it and did delete most of the branches it named. The
scheduled order (branch-sweep 07:00 Mon, rebase 08:00 Mon) is already correct;
only that day's manual sweep ran them out of order.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/669
branch: fix-branch-sweep-worktrees
worktree: /home/n/Code/codex/coga-branch-sweep-worktrees

## Implementation notes

- Agreed behavior: prune stale worktree registrations before sweeping; preserve
  live worktrees and both refs, but report confirmed merged branches in a
  distinct, prominent, non-fatal worktree-pinned outcome.
- A prune/list failure will fail the recipe rather than silently continue with
  incomplete worktree state.
- At the human's request, scope expanded to fix the unrelated suite failure:
  the packaged `code/open-pr` skill still described the removed command-ticket
  launch, so it was synced to the live skill's current registered-recipe
  contract.

## Verification

- `python -m pytest tests/test_branchcleanup.py tests/test_branchsweep.py -q`
  — 26 passed.
- The first full-suite run had 1,566 passes, 1 skip, and 1 unrelated failure:
  `tests/test_open_pr.py::test_open_pr_live_and_packaged_copies_stay_in_sync`.
  The untouched `main` checkout fails the same test because its existing live
  and packaged `code/open-pr` skill copies differ. Fixed at the human's request.
- `python -m pytest -p no:cacheprovider` — 1,567 passed, 1 skipped.

## Handoff

- `4b7750b5` implements stale-registration pruning, live-worktree detection,
  the distinct `skipped-worktree-pinned` result, fail-loud worktree-state
  errors, mirrored contracts, and real Git regression fixtures.
- `8d0010d9` separately syncs the stale packaged `code/open-pr` contract to
  fix the pre-existing suite failure requested by the human.
- Feature worktree is clean and rebased on current `origin/main`
  (`1389e837`).
- Live worktree directories remain deliberately untouched. Automatic lifecycle
  retirement remains the scope of the existing draft follow-up ticket.

## Peer review

- `codex review --base main` reported two P2 safety findings:
  1. sweep ancestry inherited retire's `HEAD`-is-control assumption, so a
     pruned stacked branch could be deleted from a feature checkout without
     landing on the configured control branch;
  2. a worktree paused in rebase appears detached in porcelain output even
     though Git still reserves its branch, allowing the remote ref to be
     deleted before local deletion failed.
- Fixed both by checking ancestry against the configured control ref, attempting
  local cleanup before remote cleanup, recognizing Git's authoritative
  worktree refusal, and requiring a successful/local-safe deletion before
  deleting the remote half.
- Added real-repository regressions for a pruned stacked branch and a conflicted
  rebase worktree. Updated the live and packaged branch-sweep workflow
  contracts.
- Peer-review fixes are committed as `9f0755ed`.
- Targeted verification after the fixes:
  `python -m pytest -q tests/test_branchcleanup.py tests/test_branchsweep.py`
  — 28 passed.
- Final verification after the unconditional fetch/rebase:
  `python -m pytest -p no:cacheprovider` — 1,569 passed, 1 skipped.

## PR

Fix branch-sweep worktree handling so stale registrations are pruned before
branch enumeration, while branches still held by live or in-progress-operation
worktrees preserve both local and remote refs and surface as
`skipped-worktree-pinned`. Fail loud on incomplete worktree state, check landed
ancestry against the configured control branch, mirror the updated
branch-sweep contracts, and sync the packaged `code/open-pr` skill to its live
registered-recipe wording.

Test plan: `python -m pytest -p no:cacheprovider` (1,569 passed, 1 skipped).
