---
slug: v2/cleanup-core-commands/work-orchestration-commands-to-tickets
title: Move work orchestration commands to tickets
status: draft
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
contexts:
  - coga/principles
  - coga/architecture
  - coga/codebase
  - coga/current-direction
  - coga/extension-model
  - coga/project-stage
  - coga/cli
  - dev/code
skills: []
workflow: code/design-then-implement
secrets: null
script: null
---

## Description

Move command behavior that performs substantive work orchestration into durable
tickets and workflows. Commands in scope: `coga retire`, `coga megalaunch`,
`coga slack`, and digest/recurring maintenance command surfaces that still own
workflow substance.

The dedicated removal ticket supersedes the project-planning portion of this
work by deleting that command outright; it is no longer a migration target.

These are the most ticket-shaped commands: they plan work, retire work, drain
work queues, notify humans, or summarize/post results. The user-facing command
should become a small creator/launcher/alias where needed; the substantive
operation should live in a ticket, workflow, skill, or script target.

## Context

Directory index: `v2/cleanup-core-commands/README`.

Existing prior art:

- `ticket` has an irreducible command head plus `bootstrap/ticket` interview and
  finalize logic.
- recurring scan has been collapsed toward `bootstrap/recurring-scan`.
- digest/autoclose/delete behavior already has script/workflow precedent.

Design the shared pattern first so `retire`, `megalaunch`, and notification/
digest operations do not each invent a different migration shape.
Do not implement all of them in one PR; after the design review, split concrete
moves by command shape if more than one command would change.

Out of scope: `skill *`, `create`, and the launch executor substrate.

## Acceptance Criteria

- [ ] The design step defines the shared creator/launcher/alias pattern for
      work-orchestration commands.
- [ ] `retire` is migrated or split into a concrete implementation follow-up
      with exact acceptance criteria.
- [ ] `megalaunch`, `slack`, and digest/recurring maintenance surfaces are
      classified and migrated where the shape is clear.
- [ ] Implementation work is split if the reviewed design touches unrelated
      command shapes.
- [ ] Human-visible side effects remain durable in ticket blackboards, logs,
      sync commits, or notification records as appropriate.
- [ ] Tests and command-reference docs/contexts are updated.

<!-- coga:blackboard -->

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
