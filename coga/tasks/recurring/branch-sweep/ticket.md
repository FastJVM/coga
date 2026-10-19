---
title: Branch sweep
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 3dce4963-67ee-4982-9e36-cbfad8f1899c
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
step: 1 (execute)
---

## Description

Delete local and remote git branches whose work has already landed, as the
safety net behind `coga retire`'s branch deletion.

`coga retire` disposes of a finished ticket's branch when it runs from the
control branch, and exits 2 rather than delete the ticket when the proofs
keep it. But it skips that cleanup off the control branch or after a Git
error, and a branch also leaks when a ticket is deleted without going
through retire, or a session dies mid-flight. Branches are clone-local: a sweep run from one
clone never sees another clone's refs. So this template is `scope: clone` —
every clone that runs `coga recurring` services it once a day for itself.
Scope and cadence are owned by
[coga/recurring/scheduling](context:coga/recurring/scheduling).

Once a day, in each clone, this template's `ticket.py` runs the branch sweep,
which:

1. prunes registrations for worktrees whose directories are gone, then
   enumerates the branches held by the remaining live worktrees,
2. enumerates every local branch and every branch on the configured git remote,
3. skips the configured control branch, the checked-out branch, the shared
   skill-update branch, and any
   branch a non-terminal ticket names anywhere in its task files — the
   ticket body, its blackboard, or an attachment — not only under a `## Dev`
   `branch:` line; a mere mention pins, because a false positive only defers
   a delete until the next pass. A recurring period task pins only its `## Dev`
   `branch:`, since its blackboard is generated reports naming branches,
4. for the rest, authorizes deletion two independent ways — the local tip
   being reachable from the control branch, a merge-commit or fast-forward
   landing that needs no PR at all, or a merged PR for that head branch name
   with no PR currently open for it, where the merged PR vouches for the
   local ref only if every commit on the ref that neither the merged head nor
   the control branch (local or remote-tracking) contains touches only Coga
   task/log state. That admits
   the exact merged tip, a ref that lags the merged head because the last
   commit was pushed from another checkout (the merged head is fetched from
   `refs/pull/<n>/head` when it is not local), and a ref that walked past the
   merged head through Coga's own state-sync commits; a ref carrying real
   unmerged source commits stays, with the offending paths named. The remote
   ref takes only a merged PR at its exact tip,
5. for a branch whose local tip landed either way but is still held by a live worktree,
   preserves both refs and reports the distinct, non-fatal
   `skipped-worktree-pinned` outcome — unless `[git].worktrees_ticket_owned`
   is `true`, the repo's declaration that every linked worktree of its git
   repository belongs to a Coga ticket. With no open PR, a landed worktree linked
   to the clone this sweep runs from, checked out on that branch, locally
   pristine (no tracked or untracked files; ignored regenerable caches are
   fine), and recorded by no non-terminal ticket qualifies for removal in
   step 6; a worktree that
   fails any of those proofs stays `skipped-worktree-pinned` with the reason,
6. publishes the retirement tag before removing the worktree or deleting
   either ref, under the archive gate in
   [dev/checkout-cleanup/branch-sweep](context:dev/checkout-cleanup/branch-sweep). Failed archival
   preserves the refs and worktree and records a failing sweep outcome.
   Then it removes the eligible worktree, reported under `removed worktree`,
   and deletes the local branch and/or remote ref under the local-before-remote
   deletion rules in
   [dev/checkout-cleanup/proofs](context:dev/checkout-cleanup/proofs) that
   `coga retire` also follows, skipping and reporting anything unmerged with no
   merged PR,
7. from the control branch, disposes of the `retires.md` entries that record
   this clone as `owner` under the
   [checkout proofs](context:dev/checkout-cleanup/proofs) autoclose runs, and
   publishes just that worklist when it discharged or refreshed one — the
   only commit this clone-scoped run makes, and
8. prints a `## Branch Sweep` report — the outcome lists and every
   per-branch decision. A clone-scoped run has no period blackboard, so the
   report is kept in the clone's `.coga/recurring-clone/branch-sweep.log` and
   in the sweep's run record for the autofix analyst.

The sweep is defined in `coga.branchsweep.sweep_branches`. The worktree
removal is a direct destructive change gated on a repo-level opt-in; the
`dev/checkout-cleanup/branch-sweep` context states the assumption the key asserts, and the
`coga/branch-sweep/sweep` skill names the proofs. Its first run
also prunes the merged part of the branch backlog that accumulated before
retire-time deletion shipped — abandoned no-PR branches are skipped and
reported by design, so expect a residual manual pass rather than a fully
clean slate. A failure to prune or list worktree state fails the sweep before
any branch deletion.

The sweep runs on this schedule via `coga recurring` in each clone, on
demand via `coga recurring launch branch-sweep`, or directly with
`coga run branch-sweep`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
