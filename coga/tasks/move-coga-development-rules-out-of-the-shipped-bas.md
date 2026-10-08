---
title: Move Coga-development rules out of the shipped base prompt
status: draft
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
contexts:
  - coga/prompt-composition
  - coga/packaging
---

## Description

The packaged base prompt (`src/coga/resources/prompt.md`) ships a section that
only makes sense when the repo being worked on is Coga itself: "Keep Coga small
and legible" (lines 98–116, 139 words). It opens with "When changing Coga
itself, preserve its microkernel boundary" and talks about `src/coga/`,
`runner.RECIPES` and wheel-owned edge modules.

Because `prompt.md` is read only from the installed package, every user gets
this section in every launch, in repos that have nothing to do with Coga. It
costs tokens on each launch and gives an agent working on someone else's
project rules about a codebase it is not in.

Move the section to where it belongs: the Coga repo's own `coga/context.md`,
which is composed into every task prompt in this repo and is currently the
untouched `coga init` template stub. Coga's own tickets keep the rule; nobody
else receives it.

Done means:

- The "Keep Coga small and legible" section is gone from
  `src/coga/resources/prompt.md`.
- Its content is in this repo's `coga/context.md`, replacing the template stub
  text, with wording adjusted so it reads as repo context rather than a
  conditional ("When changing Coga itself…" becomes a plain statement about
  this repo).
- The rest of `prompt.md` and the session-conduct layers
  (`prompt-attended.md`, `prompt-megalaunch.md`, `prompt-queue.md`,
  `prompt-blocker-resolution.md`) have been read with one question: does this
  rule make sense in someone else's repo? Each rule that only fits the Coga
  repo is moved the same way, or the reason to keep it is written on the
  blackboard.
- A test guards the boundary: the packaged prompt layers contain no reference
  to `src/coga/` or other Coga-source paths.
- Verified by composing a prompt in a fresh `coga init` repo (section absent)
  and in this repo (section present, via `coga/context.md`).

## Context

- Evidence (2026-10-07): in a fresh `coga init` repo with coga 0.4.0, the
  composed prompt for a `code/design-then-implement` ticket contains both
  "microkernel boundary" and `src/coga/`.
- `compose._resource()` reads `prompt.md` and the conduct layers through
  `paths.read_packaged_resource`, with no repo-first lookup. Workflows, skills
  and contexts do have repo-first resolution (`resolve_workflow_path`,
  `resolve_skill_path`); the base prompt does not.
- No test currently references the section text (grep for "Keep Coga small"
  and "microkernel boundary" finds only `prompt.md`).
- First read of the rest of `prompt.md`: the loop, ticket/blackboard,
  finishing the step, blocking and boundaries sections are about operating
  Coga and apply to any repo. One phrase to reconsider: the opening "this
  team's repo-level company OS" is FastJVM's framing, not necessarily a
  user's. `coga/launch` and `coga/packaging`, which the prompt cites, ship as
  bootstrap contexts, so those references resolve for users.
- Out of scope: letting a repo override `prompt.md` and the conduct layers.
  That is `overload-base-text-prompt-etc`. This one removes repo-specific
  content so the shared base is right for everyone, with or without an
  override, and comes first.
- Keep everything in this ticket's body inside `## Description` and
  `## Context`: the composer currently drops any other level-two section.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
