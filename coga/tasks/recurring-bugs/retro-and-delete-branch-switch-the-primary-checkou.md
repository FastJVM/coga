---
slug: recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou
title: retro and delete branch-switch the primary checkout, unsafe under concurrency
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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

pr: https://github.com/FastJVM/coga/pull/614
branch: fix/retro-worktree-isolation
worktree: /tmp/coga-retro-worktree-isolation

## Implementation

- Both Retro callers (`coga retire` and Dream Phase 4) now delegate the complete
  pass into an isolated checkout. Claude may use native worktree isolation;
  Codex may use a caller-created linked worktree, with an independent
  `git clone --no-hardlinks` fallback when the sandbox cannot lock primary
  `.git` metadata.
- The caller snapshots live task/corpus evidence, ordinary-copies the ignored
  `coga.local.toml` into the isolated checkout, uses the configured Git
  remote/control ref, verifies durable output, and explicitly cleans the
  config, checkout, snapshot, and temporary branch.
- `coga delete --keep-control-checkout` is accepted only in a linked worktree.
  It pushes the scoped deletion without running the normal cross-worktree local
  control-ref refresh. An independent clone uses ordinary `coga delete`, whose
  local ref namespace cannot mutate the operator checkout.
- Regression coverage pins the Retro skill, generated retire body, live and
  packaged Dream templates, primary-checkout refusal, linked-worktree deletion,
  and independent-clone deletion. Focused result: `187 passed` across the five
  affected suites.
- Final full verification: `1326 passed, 1 skipped` via
  `PYTHONPATH=/tmp/coga-retro-worktree-isolation/src python -m pytest`;
  `git diff --check main...HEAD` passes. Scoped `coga validate --task` reports
  the task clean, plus only the disposable worktree's expected missing-user
  warning.
- Commits after the final rebase: `845aedcb` (initial isolation contract),
  `5f76b3ca` (first review fixes), and `d8bf615f` (checkout fallbacks). The
  branch is clean, three commits ahead and zero behind `origin/main` at
  `1a3539f1`.

## Dream Skill: validate-drift

Generated: 2026-07-20T05:14:09+00:00
Command: `coga validate --json --fix`
Task: `recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Peer review

`codex review --base main` found four substantive gaps in the first pass:

- an isolated `coga delete` still fast-forwards the checkout holding `main`,
  mutating its ref/index/files through the sync layer;
- Codex subagents do not expose Claude's `isolation: worktree` argument, so the
  exact backend-specific contract blocks a supported agent;
- a newly created worktree starts from committed state and therefore misses
  Dream's live `## Findings` plus any other uncommitted evidence/corpus state;
- Claude retains a worktree after a mutating subagent run, contrary to the
  templates' automatic-cleanup claim.

Those findings were resolved by making the boundary backend-neutral, carrying
an explicit snapshot of live Coga state, adding the linked-worktree-only delete
mode, and requiring verified cleanup after durable output.

A second `codex review --base main` pass found three more execution gaps:

- restricted Codex could not create a linked worktree because primary `.git`
  is read-only;
- a fresh isolated checkout lacked the ignored `coga.local.toml`, so
  `coga delete` failed config loading before resolution;
- the Retro skill still hard-coded `origin/main` despite configurable Git
  remote/control settings.

All three are resolved: the contract includes the independent-clone fallback,
copies machine-local config without snapshotting or committing it, and uses the
configured control ref throughout. Real-git tests cover both linked and clone
delete paths while asserting the primary ref, index, files, and status do not
move.

## Dream Skill: validate-drift

Generated: 2026-07-20T05:54:09+00:00
Command: `coga validate --json --fix`
Task: `recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-20T06:07:33+00:00
Command: `coga validate --json --fix`
Task: `recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-20T06:20:01+00:00
Command: `coga validate --json --fix`
Task: `recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## PR

### Summary

- Run Retro and every branch switch/delete in a verified isolated checkout,
  with linked-worktree and sandbox-safe independent-clone paths.
- Preserve live evidence and machine-local config without committing either,
  use configured Git refs, and explicitly clean temporary checkout state.
- Add a linked-worktree-only delete mode that lands the remote removal without
  refreshing the operator's control checkout.

### Test Plan

`PYTHONPATH=$PWD/src python -m pytest` — 1326 passed, 1 skipped.
