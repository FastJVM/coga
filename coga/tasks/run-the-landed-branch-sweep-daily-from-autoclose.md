---
title: Run the landed-branch sweep daily from autoclose
status: in_progress
owner: nicktoper
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
---

## Description

Local branches for merged PRs pile up for up to a week. On 2026-09-24 this checkout held 49 local branches: 41 with merged PRs, 1 closed, and 20 worktree registrations pointing at wiped /tmp paths. Daily autoclose only disposes of checkouts that a ticket recorded. Ad-hoc branches and worktrees (review checkouts such as /tmp/coga-review-eight/pr873, agent scratch worktrees) are left to the weekly Monday branch-sweep, so a PR merged on Tuesday leaves its branch for six days, and longer if the sweep hits a pinned worktree. Make autoclose's daily run also apply branch-sweep's landed-branch pass (git worktree prune, then delete local and remote branches whose PR merged or closed, under the existing proofs in branchcleanup/branchsweep: no open PR, tip landed or equal to the merged PR head modulo Coga bookkeeping commits, pristine unclaimed worktree). Either fold the pass into autoclose-merged or schedule branch-sweep daily; decide which, and update dev/checkout-cleanup and coga/recurring/scheduling. Tradeoff to weigh: the weekly cadence was deliberate (daily = ticket-recorded checkouts, weekly = GC of everything else), and a daily pass adds gh API calls to every autoclose run. Done when a branch whose PR merged, with no live ticket, is gone locally and on origin after the next daily autoclose, and branches with unpushed non-bookkeeping commits are still reported, not deleted.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
