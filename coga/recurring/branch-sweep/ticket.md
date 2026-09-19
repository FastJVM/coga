---
schedule: "0 7 * * 1"
schedule_comment: "Every Monday at 7am - prune stale git branches before the day's other automation starts"
title: "Branch sweep"
# The reserved `ticket.py` sibling is this task's deterministic half: `coga
# launch` runs it directly, with no agent and no composed prompt. The one-step
# workflow keeps the period task's lifecycle and skill contract legible.
workflow: branch-sweep/sweep
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
3. skips the configured control branch, the checked-out branch, and any
   branch a non-terminal ticket names anywhere in its task files — the
   ticket body, its blackboard, or an attachment — not only under a `## Dev`
   `branch:` line; a mere mention pins, because a false positive only defers
   a delete by a week. A recurring period task pins only its `## Dev`
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
5. for a branch that landed either way but is still held by a live worktree,
   preserves both refs and reports the distinct, non-fatal
   `skipped-worktree-pinned` outcome — unless `[git].worktrees_ticket_owned`
   is `true`, the repo's declaration that every linked worktree of its git
   repository belongs to a Coga ticket. Then a landed worktree that is linked
   to the clone this sweep runs from, checked out on that branch, locally
   pristine (no tracked or untracked files; ignored regenerable caches are
   fine), and recorded by no non-terminal ticket is removed first, reported
   under `removed worktree`, and its refs continue to step 6; a worktree that
   fails any of those proofs stays `skipped-worktree-pinned` with the reason,
6. deletes the remote ref and/or local branch per the same policy
   `coga retire` uses (plain `git branch -d` when the tip is reachable from
   the control branch; log the tip SHA and force with `-D` for the
   squash-merge case a merged PR vouches for; skip and report anything
   unmerged with no merged PR), and
7. writes a `## Branch Sweep` report — the outcome lists and every
   per-branch decision — to this period task's blackboard, so the run has a
   durable record for the recurring sweep's autofix analyst; run outside a
   task, the report goes to stdout instead.

The sweep is defined in `coga.branchsweep.sweep_branches`. The worktree
removal is a direct destructive change gated on a repo-level opt-in; the
`dev/code` context states the assumption the key asserts, and the
`coga/branch-sweep/sweep` skill names the proofs. Its first run
also prunes the merged part of the branch backlog that accumulated before
retire-time deletion shipped — abandoned no-PR branches are skipped and
reported by design, so expect a residual manual pass rather than a fully
clean slate. A failure to prune or list worktree state fails the sweep before
any branch deletion.

The sweep runs on this schedule via `coga recurring`, on demand via
`coga recurring launch branch-sweep`, or directly with
`coga run branch-sweep`.

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. The
`branch-sweep` sweep keeps no durable state here — every run's
output is the branches it deletes or reports as skipped, written as a
`## Branch Sweep` section on the period task's own blackboard. `coga
recurring` keeps the serviced-period record in the repo-global `coga/log.md`
(weekly period key `YYYY-Www`) once the first run has fired.
