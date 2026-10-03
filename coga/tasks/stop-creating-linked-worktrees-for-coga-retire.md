---
title: Stop creating linked worktrees for coga retire
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

`coga retire` runs Retro (`retro/done-ticket`) in a subagent inside an
isolated checkout. It uses native `isolation: worktree` when available and
otherwise tells the caller to `git worktree add` one. Owner direction
(2026-10-02): no linked worktrees outside Coga's own recurring internals.
Hand-made or agent-made checkouts pile up on disk and are never found again.
Decide what replaces that isolation for `retire`, then build it.

Done means `coga retire` no longer creates (or tells an agent to create) a
linked worktree that can outlive the run, Retro still cannot touch the
operator's working tree or branch, and the owning instructions and topics
describe the new shape.

## Context

Split from `run-recurring-agent-templates-off-the-control-bran` (2026-10-02),
which fixes the recurring refusal text only.

- **Where the instruction lives.** `src/coga/resources/retire.md` step 1:
  copy an `evidence/` snapshot into a temp run dir, then delegate to one
  subagent in "a dedicated isolated git checkout". That means native
  `isolation: worktree`, else `git worktree add`, else
  `git clone --no-hardlinks` under `/tmp` when `.git` is read-only. The
  caller also ordinary-copies `coga.local.toml` into the checkout.
- **Shared skill.** The `retro/done-ticket` skill ("Isolation boundary"
  section; packaged at
  `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`)
  defines the same three shapes, and **Dream also uses it**
  (`<run-dir>/checkout` inside its `mktemp -d` run dir; see
  `src/coga/resources/templates/coga/recurring/dream/ticket.md`). Dream is
  recurring and allowed to keep its Coga-owned worktree. Any change must
  either leave Dream's path working or split the boundary by caller.
- **Why isolation exists.** Retro switches branches, deletes processed task
  dirs, commits, and opens knowledge PRs, without disturbing the operator's
  checkout.
- **Options to weigh in design (each costs something):**
  1. Run in the operator's checkout with `git switch`, like
     `stop-using-worktrees` did for ticket work (`dev/checkouts`). No extra
     disk, but it needs a clean tree and takes the checkout for the whole run.
  2. Temp clone under the run dir, deleted on exit. No worktree metadata, but
     it costs disk and leaves litter if cleanup fails.
  3. Coga-owned temp worktree with marker-based reaping, reusing
     `coga/internals/recurring-temp-worktrees` machinery
     (`workspace_discovery.CONTROL_WORKTREE_OWNER_FILE`, stale reaping).
     Still a worktree, but it cleans up after itself, which is the
     exception the owner allows.
  Native Claude `isolation: worktree` is created and cleaned by the agent
  harness, not by Coga. Check whether it actually leaves directories behind
  before ruling it out.
- Before choosing, run `git worktree list` on a working machine to find the
  leftover checkouts the owner reports and which path made them.
- Behavior changes update `retire.md`, the skill and its packaged twin, and
  any owning topic in the same PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
