---
title: Branch sweep
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: e905f014-903b-4c69-bdd8-bb53bcefb1e6
workflow:
  name: branch-sweep/sweep
  steps:
  - name: sweep
    skills:
    - coga/branch-sweep/sweep
    assignee: agent
---

## Description

Delete local and remote git branches whose work has already landed, as the
safety net behind `coga retire`'s branch deletion.

`coga retire` deletes a finished ticket's branch immediately, but that
cleanup is best-effort — `git`/`gh` failures are swallowed there, and a
branch also leaks when a ticket is deleted without going through retire, or
a session dies mid-flight. Retire covers the common path daily (in effect,
every time a ticket finishes); this sweep runs weekly to catch what leaks
past it.

Once a week this recurring task's `ticket.py` runs the branch sweep,
which:

1. prunes registrations for worktrees whose directories are gone, then
   enumerates the branches held by the remaining live worktrees,
2. enumerates every local branch and every branch on the configured git remote,
3. skips the configured control branch, the checked-out branch, and any branch recorded under a
   non-terminal ticket's `## Dev` `branch:` line,
4. for the rest, authorizes deletion two independent ways — the local tip
   being reachable from the control branch, a merge-commit or fast-forward
   landing that needs no PR at all, or GitHub confirming by head branch name
   and current tip SHA a merged PR for that exact tip with no PR currently
   open for that head; the remote ref takes only the second signal,
5. preserves both refs for a branch that landed either way but is still held
   by a live worktree and reports the distinct, non-fatal
   `skipped-worktree-pinned` outcome, and
6. deletes the remote ref and/or local branch per the same policy
   `coga retire` uses (plain `git branch -d` when the tip is reachable from
   the control branch; log the tip SHA and force with `-D` for the
   squash-merge case a merged PR vouches for; skip and report anything
   unmerged with no merged PR).

The sweep is defined in `coga.branchsweep.sweep_branches`. Its first run
also prunes the merged part of the branch backlog that accumulated before
retire-time deletion shipped — abandoned no-PR branches are skipped and
reported by design, so expect a residual manual pass rather than a fully
clean slate. A failure to prune or list worktree state fails the sweep before
any branch deletion.

The sweep runs on this schedule via `coga recurring`, on demand via
`coga recurring launch branch-sweep`, or directly with
`coga run branch-sweep`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
