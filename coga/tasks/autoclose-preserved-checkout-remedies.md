---
title: autoclose-preserved-checkout-remedies
status: active
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
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

Replaces closed PRs #870 and #849, both of which patched the pre-#839 'autoclose only names a retire follow-up' design. Since #839, `coga run autoclose` runs the shared disposal proofs itself (`_dispose_checkouts` over `checkout_disposal` / `branchcleanup`) and reports each refusal with `CheckoutOutcome.disposal.reason` and `CheckoutOutcome.manual_command`. Two refusals still produce advice a human cannot act on:

1. **Cross-repo worktree (#870's case).** A ticket whose recorded `worktree:` belongs to another git repository is refused as 'not a linked worktree of this repository' and `manual_command` still says `coga retire <slug>` — which fails the same proof from this repo, and the task does not exist in the owning repo. Resolve the recorded path to its owning checkout (the `--git-common-dir` comparison retire already makes) and name that checkout plus the by-hand `git -C <owner> worktree remove` / `branch -d` there; a path gone from disk or not a git worktree should say so and point at branch-only cleanup.

2. **Primary checkout recorded as `worktree:` (#849's case).** In the single-checkout layout the ticket records the primary checkout itself. The proof refuses it forever (the primary checkout is always a directory and never a linked worktree), so the entry is preserved, re-posted to coga-important on every run, and once retro deletes the ticket the worklist header tells a human to dispose of it by hand — which here means the repo. Such an entry should not count as retire debt: drop the worktree half when it is provably not a linked worktree retire could remove (a tri-state `git.is_linked_worktree_of`, so retire keeps its own preserve-on-doubt fail-safe), leaving a branch-only follow-up or none.

The closed PRs carry reviewed prose and tests for both rules (autoclose/sweep skill, `test_autoclose.py`, `test_retire_worklist.py`) that can be re-applied on top of the disposal-phase design. Keep the live and packaged twins of the autoclose/sweep skill and the autoclose-merged template in sync.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
