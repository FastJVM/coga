---
slug: recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou
title: retro and delete branch-switch the primary checkout, unsafe under concurrency
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

Retro and delete operate on the **primary checkout** with branch switches and
direct commits to the control branch, which is unsafe when that tree is shared
with concurrent agents (or when another checkout of the same remote is active).

Observed 2026-07-17: the `xpllm` `recurring/dream` run reached Phase 4 (retro)
and **blocked itself** rather than proceed, because it detected concurrent
sessions committing to `main` in the same working tree. The concrete hazards
it identified:

- `retro/done-ticket` (step 11) runs `git checkout -b <branch> origin/main` on
  the *current checkout*, makes edits, commits, and switches back to `main`.
- `coga delete` commits `Ticket: <slug> — deleted` directly to the control
  branch.
- Phase 4 would do this across **34** done tickets in one run.

With live concurrent `coga` committers in the same checkout, a concurrent
commit can land on the retro branch mid-run, and the checkout switch can
entangle another agent's uncommitted work — a real corruption/interleave risk.

**Fix direction:** run retro (and the delete it performs) in an **isolated git
worktree** rather than mutating the primary checkout's HEAD — the same
`isolation: worktree` shape used elsewhere for parallel mutating agents — or,
at minimum, refuse to branch-switch when the working tree is dirty / another
coga session holds the checkout, and fail loud with an actionable message.
The goal: retro must never leave the operator's primary checkout on a
surprise branch or with interleaved commits.

## Context

- Retro skill: `retro/done-ticket` (step 11 branch-switch). Invoked via
  `coga retire` (`src/coga/commands/retire.py` / the retire task body).
- Delete: `coga delete` → `bootstrap/delete-task` skill, commits directly to
  the control branch (`src/coga/commands/delete.py`).
- Dream Phase 4 (retro pass) is the highest-volume caller — see the
  `coga/recurring/dream/` template body.
- Precedent for isolation: the Agent/worktree `isolation: worktree` pattern
  (auto-cleaned worktree) is the natural fit.
- Related but distinct: `recurring-bugs/recurring-all-diverges-two-checkouts-of-one-remote`
  is about recurring *bookkeeping* diverging; this ticket is about retro/delete
  *branch-switching* the shared checkout.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Recovery

The 2026-07-17 megalaunch attempt made no source changes. It stated a sound
implementation plan, asked "Shall I proceed?", and then waited until the
idle-timeout backstop ended the session.

Owner authorization is explicit: resume the implement step, apply the proposed
isolation fix, and do not pause again for plan approval. Continue on reasonable
implementation assumptions; only a concrete decision or unavailable capability
should end in `coga block`. Finish the step with `coga bump` after the committed
code and blackboard handoff are complete.

Systemic queue guidance and exact timeout reporting are proposed in
https://github.com/FastJVM/coga/pull/597; this ticket still owns its original
retro/delete isolation fix.

## Dev

branch: fix/retro-worktree-isolation
worktree: /tmp/coga-retro-worktree-isolation

## Implementation

- Keep isolation prompt-level: Coga has no workflow/runtime `isolation` field;
  `isolation: worktree` is the existing subagent delegation contract.
- Require both Retro callers (`coga retire`'s generated body and Dream Phase 4)
  to delegate the complete pass into one isolated worktree.
- Make `retro/done-ticket` fail loud unless it is already running inside that
  isolated worktree; all branch switches and Retro-triggered `coga delete`
  calls stay within it, and automatic teardown restores the caller checkout.
- Regression coverage now pins all three boundaries: the Retro skill, the
  generated `coga retire` body, and packaged Dream Phase 4. Focused result:
  `18 passed` across `test_retro_skill_template.py`,
  `test_dream_worker_templates.py`, and `test_retire.py`.
- Full verification from the feature worktree: `1323 passed, 1 skipped` via
  `PYTHONPATH=<feature>/src python -m pytest`; `git diff --check` also passes.
- Commit: `4c434accdc25c4ad9a254664031c730bf29fda30` (`Require worktree
  isolation for Retro runs`). The worktree is clean and one commit ahead of
  `origin/main`.
- Freshness: fetched `origin/main` at `c2ff4eca` and rebased onto `FETCH_HEAD`;
  the branch was already current, so no post-rebase test rerun was needed.

## Dream Skill: validate-drift

Generated: 2026-07-20T05:14:09+00:00
Command: `coga validate --json --fix`
Task: `recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
