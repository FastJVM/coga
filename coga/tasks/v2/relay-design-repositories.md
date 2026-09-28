---
title: relay-design-repositories
status: paused
owner: zach
agent: claude
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Decide and, if still wanted, build the part of repository design that shipped
onboarding does not cover: an interview that elicits what the repo is for
(the direction it advances, not a deliverable to finish), the gap it closes
("what doesn't exist today that this is trying to create?"), and which
existing skills and workflows the repo should lean on — then creates the
repository from those answers.

Already delivered, to reuse rather than rebuild: `coga build` onboarding
(`coga/workflows/build/onboarding.md`, `gather-and-spec` and
`generate-batch`) interviews the operator in an empty repo, records the
agreed `product/vision` context, and generates starter tickets. The original
proposal (a `relay design` command) also asked for those pieces.

## Context

Acceptance criteria attach to the generated tickets, not to the repository
— the repo is a direction, not a deliverable. Nearest existing patterns to
lean on: `relay init` already creates repos, and `bootstrap/ticket` already
runs an interview-and-create flow; this is closer to the latter applied at
repo scope.

### Premise review — 2026-09-28

Kept, and narrowed above, by `adjudicate-the-eight-premise-dead-v2-drafts`
(owner-approved table). Delivery is partial, not settled:

- `coga build` is an alias for `launch` of the onboarding task
  (`aliases.DEFAULT_ALIASES`); PR #701 (`ef721d2f`) restored onboarding and
  left the old project command removed. `commands.init._do_init` seeds that
  onboarding only for an empty repo.
- Correction to the paragraph above: `coga init` does **not** create
  repositories. It requires an existing git worktree and refuses outside one.
  Creating a repository from interview answers therefore has no current
  precedent.
- Onboarding does not require the direction/gap framing or selection from
  existing skills and workflows. Packaged `bootstrap/ticket` remains the
  closest interview-and-create precedent at ticket scope.
- The log records this draft's creation, activation and 2026-07-01 pause;
  nothing settles the remainder.

Acceptance criteria still attach to generated tickets, not the repository.
Whether to extend onboarding or keep a separate operation, and whether repo
creation is still wanted, are left to this ticket's owner-led design.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
