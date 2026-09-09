---
name: coga/branch-sweep/sweep
description: Delete local and remote git branches whose work has already landed.
---

# Branch Sweep

This skill documents the branch sweep behind the
`recurring/branch-sweep/` ticket, whose `ticket.py` calls
`coga.branchsweep.run_branch_sweep_recipe` directly — no agent, no composed
prompt. It is the safety net behind `coga retire`'s
branch deletion — retire's
cleanup is best-effort (failures are swallowed), and branches also leak when
a ticket is deleted without going through retire or a session dies mid-flight.

1. prune registrations for worktrees whose directories are gone (`git
   worktree prune`), then enumerate the branches held by the remaining live
   worktrees,
2. enumerate every local branch and every branch on `[git].remote`,
3. skip `[git].control_branch`, the checked-out branch, and any branch recorded under a
   non-terminal ticket's `## Dev` `branch:` line,
4. for the rest, authorize deletion two independent ways: the local tip being
   reachable from `[git].control_branch`
   (`branchcleanup.local_branch_landed`) — a real merge-commit or
   fast-forward landing, which needs no PR at all — or GitHub confirming, by
   **head branch name** and current tip SHA (`gh pr list --head <branch>` with
   `headRefOid`), a merged PR for that exact tip and no PR currently open for
   that head (`branch_merged_without_open_pr`). The remote ref takes only the
   second signal: ancestry never authorizes deleting `<remote>/<branch>`,
5. preserve both refs for a branch that landed either way but is still held by
   a live worktree, and report it under the distinct, non-fatal
   `skipped-worktree-pinned` outcome,
6. delete the remote ref (`git push <configured-remote> --delete`) when a
   merged PR covers its tip, and the local branch following the same policy
   retire uses: plain `git branch -d` on the ancestry path, or a logged `-D`
   — after re-reading the ref and preserving the branch if it moved off the
   authorized tip — for the squash-merge case, where the merged PR is the only
   thing vouching for the work.

The scope is defined by `coga.branchsweep.sweep_branches`. If worktree state
cannot be pruned/listed, the sweep fails before deleting anything. If `gh` is
missing or unauthed, the sweep fails and performs no further gated deletes —
never a delete with incomplete safety information.

Run it directly with `coga run branch-sweep`.
