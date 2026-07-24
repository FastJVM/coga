---
schedule: "0 7 * * 1"
schedule_comment: "Every Monday at 7am - prune stale git branches before the day's other automation starts"
title: "Branch sweep"
recipe: branch-sweep
# The recurring runner executes this registered recipe directly with no agent.
# The one-step workflow keeps the period task's lifecycle and skill contract
# legible.
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

Once a week this recurring task's recipe runs the branch sweep, which:

1. enumerates every local branch and every branch on the configured git remote,
2. skips the configured control branch, the checked-out branch, and any branch recorded under a
   non-terminal ticket's `## Dev` `branch:` line,
3. for the rest, checks GitHub by head branch name and current tip SHA —
   deletes only when a merged PR exists for that exact tip and no PR is
   currently open for the head branch, and
4. deletes the remote ref and/or local branch per the same policy
   `coga retire` uses (prefer `git branch -d`; log the tip SHA and force
   with `-D` for the squash-merge case; skip and report anything unmerged
   with no merged PR).

The sweep is defined in `coga.branchsweep.sweep_branches`. Its first run
also prunes the merged part of the branch backlog that accumulated before
retire-time deletion shipped — abandoned no-PR branches are skipped and
reported by design, so expect a residual manual pass rather than a fully
clean slate.

The sweep runs on this schedule via `coga recurring`, on demand via
`coga recurring launch branch-sweep`, or directly with
`coga run branch-sweep`.

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. The
`branch-sweep` recipe keeps no durable state here — every run's
output is the branches it deletes or reports as skipped. `coga recurring`
keeps the serviced-period high-water mark here as `last_serviced_period`
(weekly period key `YYYY-Www`) once the first run has fired.

last_serviced_period: 2026-W30
