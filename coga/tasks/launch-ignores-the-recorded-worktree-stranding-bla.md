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

`coga launch` never chooses where a step's agent runs — the child inherits the
supervisor's cwd — while the shipped `code/implement` skill tells that agent to
`cd` into the feature worktree. Read literally the skill is consistent (it says
to return to the primary checkout before writing `## Dev` and before `coga
bump`), but nothing verifies the agent came back. When it doesn't, implement's
blackboard writes land on the feature branch and the next step respawns in the
primary checkout and cannot see them, so `open-pr` fails with "No usable
`branch:` recorded" even though implement did record it.

This is therefore an **enforcement/compliance** bug — an unverified instruction,
not a contradiction between `launch` and the skill. Any fix has to say what
makes the write and the read agree on one checkout.

## Context

Citations below were verified against the source on 2026-08-14; an earlier draft
of this ticket cited wrong lines, so trust these and re-check before relying on
any line number quoted elsewhere.

- Write side — nobody chooses the cwd: `spawn_agent_session` calls
  `run_with_done_marker(cmd, env, ...)` at `commands/launch.py:2052`, and
  `repl_supervisor.py:202` takes **no `cwd` parameter at all**. There is no
  `os.chdir` anywhere in `src/coga/`. The child inherits the supervisor's cwd by
  omission. A fix at this layer means threading `cwd=` through shared spawn
  infra — a signature change, not a one-line edit.
- `launch` **does** already read `worktree:`, contrary to earlier notes:
  `_recorded_single_checkout_assist_branch` (`commands/launch.py:1555-1586`)
  calls `parse_worktree_path` and requires `same_git_checkout(cfg.repo_root,
  worktree)` before authorizing the single-checkout PR assist. The accurate
  claim is narrow: launch reads `worktree:` to *authorize* the assist path, and
  never to *place* the child process.
- Read side: the `worktree:` read is `open_pr.py:321` (error at `:324`); the
  observed `branch:` failure is `open_pr.py:315`. `parse_worktree_path` is
  *defined* in `autoclose.py:101` but consumed by `branchcleanup.py:133`,
  `open_pr.py:321` and `:589`, `commands/retire.py:280`, and
  `commands/launch.py:1573`. `branchsweep.py` does not read the line — it
  enumerates live worktrees from Git. That consumer list is the blast radius of
  any change to what `worktree:` means.
- The `cd` is mandated, not optional: `code/implement/SKILL.md:68` ("Implement
  in the worktree"), recorded per `:34`, with `:32` and `:88` telling the agent
  to return to the primary checkout before the `## Dev` write and before `coga
  bump`. Nothing verifies it — no worktree check in `validate.py` or `bump.py`.
- `git.py:sync_task_state` (`:382`, docstring `:403-412`) already lands
  feature-branch task state on control via working-tree-free plumbing, and it is
  not gated. The real gap is downstream: `bump.py:130` syncs `ref.path` — the
  ticket dir of *the checkout bump ran from*. An agent that writes `## Dev` in
  the worktree and then returns to primary before bumping makes bump faithfully
  sync a `ticket.md` that never saw the write.
- Evidence lives outside this repo and is not inspectable from here: two
  occurrences on 2026-08-08 across the `FastJVM/admin` and
  `accounting/xero-reconcile` workspaces — the `open-pr` failure above, then a
  `ticket.md` merge conflict on their PR #90 (not a PR in this repo), the same
  divergence surfacing from the other side. The reproduction has to be
  constructed locally.
- Adjacent but not covering: `v2/reintroduce-per-launch-worktree-isolation`
  (scoped to the per-launch worktrees removed in PR #547, not the
  agent-created one `code/implement` mandates today) and
  `v2/use-worktree-when-starting-a-dev-task` (placement + litter). **Both are
  placeholders — unrefined idea capture, both still `status: draft`, neither
  approved or scheduled.** Read them for prior thinking only. This ticket is the
  live one on `worktree:`; do not treat either as a committed design, a
  constraint on the fix, or a reason to narrow scope, and do not edit them.
- The contract this violates is the attached `dev/code` context — read its
  checkout-boundary, retire, and `## Dev` grammar sections; all three constrain
  the fix.
- **First reproduce, then choose.** Because the skill read literally does not
  strand anything, the `design` step must first characterize the actual
  deviation — which write landed in which checkout — before selecting a fix.
  Don't design against an unconfirmed mechanism.
- Design is genuinely open. Candidates, with what is already known against each:
  (a) `launch` places the agent in `worktree:` — but this inverts the `dev/code`
  contract for *every* step, not just implement: `ticket.md`, `coga/log.md`,
  `bump`, `slack`, `block` would all default to the feature checkout, and the
  workflow's own `open-pr` section requires the control checkout. (a) fixes
  implement by breaking open-pr; carry that objection.
  (b) `code/implement` stops mandating the `cd` and edits the worktree from the
  primary checkout.
  (c) make the write and the sync agree on one checkout (note `sync_task_state`
  is already ungated — the gap is `bump.py:130` syncing the cwd's ticket dir).
  (d) a `bump`/`validate` guard that fails loudly on divergence.
  Say what each gives up, don't just pick.
- **Converge on one fix.** The option set above is more than one ticket's worth
  of work — (a) is a signature change on shared spawn infra, (d) is an afternoon.
  Design picks exactly one; spin the rest out as follow-up tickets. Out of scope:
  implementing more than the selected option.
- Must not break the deliberate single-checkout assist layout (`launch.py:469-530`
  and `:1555`), where the primary checkout *is* the recorded worktree and launch
  publishes to the PR branch.
- Repo conventions live in `CLAUDE.md`; read the `coga/codebase` context before
  editing `src/coga/` (microkernel rule, source layout, test expectations), and
  the `coga/sync` context for `sync_task_state`'s full contract. Neither is
  attached — both are large and the pointer is enough.
- If the fix touches shipped OS files (`coga/skills/code/implement/SKILL.md`,
  workflows, contexts), mirror the change into the packaged copy under
  `src/coga/resources/templates/coga/` in the same PR.
- Chicken-and-egg to expect: this ticket's own `implement` step runs through the
  exact path being fixed, so the implementing agent may strand its own
  blackboard writes. Write `## Dev` from the primary checkout only, push the
  branch, and confirm `git show <control-branch>:coga/tasks/<slug>.md` contains
  the `branch:` line before bumping into `open-pr`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
