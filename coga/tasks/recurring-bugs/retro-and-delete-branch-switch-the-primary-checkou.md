---
slug: recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou
title: retro and delete branch-switch the primary checkout, unsafe under concurrency
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
