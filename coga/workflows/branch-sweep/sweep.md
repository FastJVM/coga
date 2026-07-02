---
name: branch-sweep/sweep
description: One-step script workflow that deletes local and remote git branches whose work has already landed.
steps:
  - name: sweep
    skills:
      - coga/branch-sweep/sweep
    assignee: agent
---

## sweep

Script step. Runs `coga/branch-sweep/sweep`, which calls
`coga.branchsweep.sweep_branches`: enumerate local and `origin` branches,
skip `main`, the checked-out branch, and any branch recorded on a
not-`done` ticket, then delete the rest when GitHub confirms (by branch
name) a merged PR with no open PR. The command exits successfully when
there is nothing to delete.
