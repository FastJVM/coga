---
name: branch-sweep/sweep
description: One-step lifecycle for the branch-sweep recurring task's deterministic half.
steps:
  - name: sweep
    skills:
      - coga/branch-sweep/sweep
    assignee: agent
---

## sweep

Script-backed recurring task. `coga launch` runs the period task's reserved
`ticket.py`, which calls `coga.branchsweep.sweep_branches`: prune missing-worktree
registrations, enumerate local/remote branches and live worktrees, skip the
configured control branch, the checked-out branch, the shared skill-update
branch, and any branch a
non-terminal ticket names, then delete branches that landed on the control
branch or that a merged PR with no open PR vouches for — the ref may carry
only Coga state commits beyond the merged head. A landed branch held by a
live worktree preserves both refs and reports `skipped-worktree-pinned`;
incomplete worktree state fails the sweep. Every deletion first passes the
retirement-tag publication gate in
[dev/checkout-cleanup](context:dev/checkout-cleanup). A failed archive keeps
the refs and worktree and makes the recipe fail with a recorded reason. The
run's report lands on this period task's blackboard.
