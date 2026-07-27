---
name: branch-sweep/sweep
description: One-step lifecycle for the branch-sweep recurring recipe.
steps:
  - name: sweep
    skills:
      - coga/branch-sweep/sweep
    assignee: agent
---

## sweep

Recipe-backed recurring task. `coga recurring` runs `coga run branch-sweep`,
which calls `coga.branchsweep.sweep_branches`: enumerate local and `origin` branches,
skip `main`, the checked-out branch, and any branch recorded on a
non-terminal ticket, then delete the rest when GitHub confirms (by branch
name and current tip SHA) a merged PR with no open PR. The command exits
successfully when there is nothing to delete.
