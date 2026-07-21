---
slug: allow-open-pr-when-the-recorded-worktree-is-the-pr
title: Allow open-pr when the recorded worktree is the primary checkout
status: draft
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

`coga open-pr` is jointly unsatisfiable when a repo develops in its primary checkout instead
of a linked worktree:

- `commands/open_pr.py::_require_control_checkout` refuses unless `cfg.repo_root` is checked
  out on the control branch.
- `open_pr.py::open_pr` refuses unless the recorded `## Dev` `worktree:` is checked out on the
  recorded feature branch.

When the recorded worktree *is* the primary checkout, those are the same git checkout: on the
control branch the recipe's branch check fails, on the feature branch the wrapper's gate fails.
The command can never run, and the workflow's `open-pr` step dead-ends in a blocker.

This is not an edge case: worktree-based development is being retired, so the recorded
`worktree:` being the primary checkout is the standard layout going forward, and open-pr's
control-checkout gate is a worktree-era assumption.

Fix: in `_require_control_checkout`, when the task's recorded `worktree:` resolves to the same
checkout as `cfg.repo_root`, skip the control-branch requirement — with a single checkout there
is no second copy of the ticket for blackboard writes to diverge from, which is the trap the
gate exists to prevent. Legacy cross-worktree layouts keep the existing gate. Cover both
layouts with tests, and audit open-pr's docstrings/messages for the retired worktree≠checkout
assumption while there.

## Context

- Hit for real by `staticization/capture-and-correlate-generated-classes` in the magicator2
  repo (blocker id=20260720T183536): that repo's `AGENTS.md` forbids linked worktrees and
  fallback clones, so `## Dev` records the primary checkout path as `worktree:` and the
  feature branch is checked out there.
- The rest of the workflow already tolerates single-checkout mode: implement, peer-review, and
  every `coga bump`/`coga block` on that ticket ran from the primary checkout while on the
  feature branch, committing ticket state onto it. Only `open-pr` hard-gates on the control
  branch.
- The recipe's freshness check (`check_branch_contains_control`) already accepts
  non-overlapping generated `coga/tasks/**` / `coga/log.md` drift between branches, so
  accepting the same-checkout layout is consistent with the existing contract.
- The wrapper docstring states the design assumption to revisit: it "operates on the `## Dev`
  feature branch by name, pushing from the recorded worktree rather than the process's own
  checkout" — which presumes worktree ≠ control checkout.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
