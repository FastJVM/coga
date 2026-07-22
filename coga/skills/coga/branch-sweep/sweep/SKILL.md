---
name: coga/branch-sweep/sweep
description: Delete local and remote git branches whose work has already landed.
script: run.py
---

# Branch Sweep

This skill is the script body of the `recurring/branch-sweep/`
ticket. It is the safety net behind `coga retire`'s branch deletion — retire's
cleanup is best-effort (failures are swallowed), and branches also leak when
a ticket is deleted without going through retire or a session dies mid-flight.

1. enumerate every local branch and every branch on `[git].remote`,
2. skip `[git].control_branch`, the checked-out branch, and any branch recorded under a
   non-terminal ticket's `## Dev` `branch:` line,
3. for the rest, check GitHub by **head branch name** and current tip SHA
   (`gh pr list --head <branch>` with `headRefOid`): delete only when a
   merged PR exists for that exact tip and no PR is currently open for the
   head branch,
4. delete the remote ref (`git push <configured-remote> --delete`) when authorized, and
   the local branch (`git branch -d`, or logged `-D` for the squash-merge
   case) following the same policy retire uses.

The scope is defined by `coga.branchsweep.sweep_branches`. If `gh` is
missing or unauthed, the rest of the run reports skipped branches and
deletes nothing — never a forced delete without a confirmed merge.

The script imports `coga.branchsweep.sweep_branches` and calls it directly,
so it does not depend on `coga` being on `PATH` inside the script
environment.
