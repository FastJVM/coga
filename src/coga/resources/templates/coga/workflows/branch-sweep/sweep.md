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
which calls `coga.branchsweep.sweep_branches`: prune missing-worktree
registrations, enumerate local/remote branches and live worktrees, skip the
configured control branch, the checked-out branch, and any branch recorded on
a non-terminal ticket, then delete branches that landed on the control branch
or whose exact tip GitHub confirms merged with no open PR. A landed branch
held by a live worktree preserves both refs and reports
`skipped-worktree-pinned`; incomplete worktree state fails the recipe.
