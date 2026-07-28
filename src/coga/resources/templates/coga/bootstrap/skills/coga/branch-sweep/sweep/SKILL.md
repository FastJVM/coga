---
name: coga/branch-sweep/sweep
description: Delete local and remote git branches whose work has already landed.
---

# Branch Sweep

This skill documents the `branch-sweep` recipe used by the
`recurring/branch-sweep/` ticket. It is the safety net behind `coga retire`'s
branch deletion — retire's
cleanup is best-effort (failures are swallowed), and branches also leak when
a ticket is deleted without going through retire or a session dies mid-flight.

1. prune registrations for worktrees whose directories are gone (`git
   worktree prune`), then enumerate the branches held by the remaining live
   worktrees,
2. enumerate every local branch and every branch on `[git].remote`,
3. skip `[git].control_branch`, the checked-out branch, and any branch recorded under a
   non-terminal ticket's `## Dev` `branch:` line,
4. for the rest, check GitHub by **head branch name** and current tip SHA
   (`gh pr list --head <branch>` with `headRefOid`): delete only when a
   merged PR exists for that exact tip and no PR is currently open for the
   head branch,
5. preserve both refs for a merged branch still held by a live worktree and
   report it under the distinct, non-fatal `skipped-worktree-pinned` outcome,
6. delete the remote ref (`git push <configured-remote> --delete`) when authorized, and
   the local branch (`git branch -d`, or logged `-D` for the squash-merge
   case) following the same policy retire uses.

The scope is defined by `coga.branchsweep.sweep_branches`. If worktree state
cannot be pruned/listed, the recipe fails before deleting anything. If `gh` is
missing or unauthed, the recipe fails and performs no further gated deletes —
never a delete with incomplete safety information.

Run it directly with `coga run branch-sweep`.
