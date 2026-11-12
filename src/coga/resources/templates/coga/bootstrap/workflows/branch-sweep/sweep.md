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

Kept for compatibility: the packaged `branch-sweep` template is `scope: clone`
and names no workflow, so its runs create no period task and never enter this
lifecycle ([coga/recurring/scheduling](context:coga/recurring/scheduling) owns
scope). This step serves only a period task from a pre-clone-scope definition.
There `coga launch` runs the reserved `ticket.py`, which runs the `branch-sweep`
recipe (`coga.branchsweep.sweep_branches`) and bumps the task: prune missing-worktree
registrations, enumerate local/remote branches and live worktrees, skip the
configured control branch, the checked-out branch, the shared skill-update
branch, and any branch a
non-terminal ticket names, then delete branches that landed on the control
branch or that a merged PR with no open PR vouches for — the ref may carry
only Coga state commits beyond the merged head. A landed branch held by a
live worktree preserves both refs and reports `skipped-worktree-pinned`;
incomplete worktree state fails the sweep. Every deletion first passes the
retirement-tag publication gate in
[coga/checkout-cleanup/branch-sweep](context:coga/checkout-cleanup/branch-sweep). A failed archive keeps
the refs and worktree and makes the recipe fail with a recorded reason. Such a
legacy run's report lands on the period task's blackboard; a clone-scoped run
keeps it in the clone's `.coga/recurring-clone/branch-sweep.log` and the run
record. The full sweep, including the clone-owned `retires.md` settlement, is
owned by the `coga/branch-sweep/sweep` skill and
the `recurring/branch-sweep` template.

## No other-agent code review

This is the one-step lifecycle of a recurring task's deterministic
half. It produces no code, so no `other-agent` step reviews it.
