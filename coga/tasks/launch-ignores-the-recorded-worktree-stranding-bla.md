---
slug: launch-ignores-the-recorded-worktree-stranding-bla
title: Launch ignores the recorded worktree, stranding blackboard writes
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/design-then-implement
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
- The checkout-boundary contract this violates is the attached `dev/code`
  context: control-plane writes (`ticket.md`, `coga/log.md`, `bump`, `slack`,
  `block`) belong in the primary checkout; source changes belong in the feature
  worktree recorded as `worktree:`. The bug is that nothing enforces the split.
- Design is genuinely open — the `design` step should pick among at least:
  (a) `launch` reads `worktree:` and spawns the agent there;
  (b) `code/implement` stops mandating the `cd` and edits the worktree from the
  primary checkout; (c) `sync_task_state` fires unconditionally so blackboard
  writes land on control wherever the agent sits; (d) a `bump`/`validate` guard
  that fails loudly on divergence. Say what each gives up, don't just pick.
- Repo conventions live in `CLAUDE.md`; read the `coga/codebase` context before
  editing `src/coga/` (microkernel rule, source layout, test expectations). It
  is deliberately not attached — it is large and the pointer is enough.
- If the fix touches shipped OS files (`coga/skills/code/implement/SKILL.md`,
  workflows, contexts), mirror the change into the packaged copy under
  `src/coga/resources/templates/coga/` in the same PR.
- Chicken-and-egg to expect: this ticket's own `implement` step runs through the
  exact path being fixed, so the implementing agent may strand its own
  blackboard writes. Push the branch and verify `ticket.md` state landed on the
  control branch before bumping into `open-pr`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
