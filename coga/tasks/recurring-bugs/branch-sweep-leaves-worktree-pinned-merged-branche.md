---
slug: recurring-bugs/branch-sweep-leaves-worktree-pinned-merged-branche
title: Branch-sweep leaves worktree-pinned merged branches behind
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
