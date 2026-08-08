---
slug: launch-ignores-the-recorded-worktree-stranding-bla
title: Launch ignores the recorded worktree, stranding blackboard writes
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

`coga launch` spawns every step's agent in the invoking cwd and never reads the
`worktree:` line, while the shipped `code/implement` skill tells that agent to
change into the feature worktree — so implement's blackboard writes land on the
feature branch while its `coga bump` updates control. The next step respawns in
the primary checkout and cannot see them, so `open-pr` fails with "No usable
`branch:` recorded" even though implement did record it.

## Context

- Write side is cwd-determined: `commands/launch.py:928,1014` (`Path.cwd()`);
  `grep worktree commands/launch.py` returns nothing.
- Read side is `worktree:`-determined: `open_pr.py:315`, and the same line is
  read by `autoclose.py`, `branchsweep.py`, `branchcleanup.py`.
- The `cd` is mandated, not optional: `code/implement/SKILL.md:68` ("Implement
  in the worktree"), recorded per `:34`. Nothing verifies it — no worktree
  check in `validate.py` or `bump.py`.
- Narrows the fix: `git.py:sync_task_state` already lands feature-branch task
  state on control via working-tree-free plumbing. The capability exists; what
  is missing is that whether it fires depends on the agent's cwd.
- Observed twice on one task (`FastJVM/admin`, `accounting/xero-reconcile`,
  2026-08-08): the `open-pr` failure above, then a `ticket.md` merge conflict
  on PR #90 — the same divergence surfacing from the other side.
- Adjacent but not covering: `v2/reintroduce-per-launch-worktree-isolation`
  (scoped to the per-launch worktrees removed in PR #547, not the
  agent-created one `code/implement` mandates today) and
  `v2/use-worktree-when-starting-a-dev-task` (placement + litter).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
