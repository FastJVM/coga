---
slug: add-a-nothing-to-implement-close-path-so-already-s
title: Add a nothing-to-implement close path so already-satisfied tickets don't park
  as blocked
status: active
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

When an agent runs an implement-step ticket and finds there is **nothing to
implement** — every checklist item already landed via other merged work, so
there is no branch and no diff — it currently has no legitimate way to close the
ticket. `coga bump` refuses to close final-step tickets (`bump.py:132-138`),
`coga mark done` is owner-reserved by the `code/with-self-review` contract, and
no skill covers the empty-work case. The only escape hatch the implement skill
gives is `coga block` (`code/implement/SKILL.md:47-55`), so the agent overloads
`block` — whose real semantics are "I need a concrete human answer to proceed" —
to mean "there's nothing to do, please close this." The already-complete ticket
then parks at `status: blocked` and pollutes the `coga status --blocked` queue
until the owner manually unblocks + marks done.

Real example that motivated this: `coga-rename-follow-ups-post-repo-rename` —
the agent verified all items had landed, created a follow-up tracking ticket,
and then had to `block` for closure. It showed up as a spurious "blocker" in the
queue even though nothing was actually blocking anything.

Goal: give the flow a first-class "already satisfied / nothing to implement →
close" path so this outcome lands as done (or a distinct resolved state), not as
`blocked`.

## Approach options (decide during authoring)

1. **Skill guidance + distinct closure request.** Teach `code/implement` (and
   `code/self-qa`) the empty-work case: write the per-item evidence to the
   blackboard and raise a *closure request* that is visually/statefully distinct
   from a `block` (not shown in the blocked queue as a "reason"), which the owner
   confirms into `done`.
2. **New status/transition.** Add an agent-allowed transition (e.g.
   `coga mark superseded` / `resolved:obsolete`, or an agent "propose done" that
   the owner one-tap confirms) so already-landed work doesn't masquerade as
   blocked. Keep `done` owner-gated but make the proposal explicit.

Either way, the `coga status --blocked` view should stop surfacing
"nothing-to-do" tickets as blockers.

## Touchpoints

- `src/coga/commands/bump.py` (final-step close refusal, chaining)
- `src/coga/commands/mark.py` (`_DONE_FROM`, owner gating), `commands/block.py`
- `coga/skills/code/implement/SKILL.md`, `coga/skills/code/self-qa/SKILL.md`
- `coga/workflows/code/with-self-review.md` (owner-controlled review gate)
- Keep the shipped copies in sync: `src/coga/resources/templates/coga/...`
- Update the matching `coga/contexts/coga/` context if behavior changes.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
