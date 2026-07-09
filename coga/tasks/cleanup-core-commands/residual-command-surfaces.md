---
slug: cleanup-core-commands/residual-command-surfaces
title: Classify residual command surfaces
status: draft
mode: agent
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

Classify the command surfaces that are easy to miss in the core-command cleanup
because they are already partially extracted, aliases, grouped commands, or
bootstrap-adjacent. Surfaces in scope: `coga init`, `coga ticket`, `coga delete`,
`coga skill *`, bare `coga recurring`, `coga recurring launch <name>`, and the
default aliases `chat`, `build`, `dream`, `skill-update`, and `autoclose`.

This ticket is not expected to migrate `skill *`; owner direction currently
excludes skills from the ticketization push. It should still classify `skill *`
so the final command taxonomy is complete and honest.

## Context

Directory index: `cleanup-core-commands/README`.

This ticket exists because the first child-ticket split covered the obvious
command groups but missed surfaces that are already partly extracted or hidden
behind aliases. Read `src/coga/cli.py`, `docs/cli-extension-audit.md`,
`coga/contexts/coga/extension-model/SKILL.md`, and packaged
`src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`.

Design first. Decide for each surface whether it is:

- true bootstrap substrate (`init` may be, because it exists before `coga/`);
- an irreducible command head plus bootstrap ticket/script body (`ticket`);
- already script-shaped and only needing docs/taxonomy updates (`delete`);
- excluded external/tooling surface (`skill *`);
- alias sugar over an existing launch/recurring launch path.

## Acceptance Criteria

- [ ] The residual surfaces are represented in the final command taxonomy.
- [ ] Default aliases are documented as alias sugar, not command logic.
- [ ] `skill *` is explicitly classified as excluded or external/tooling, with
      the owner direction recorded.
- [ ] Any migration discovered here is split into a concrete follow-up ticket
      rather than bundled into this classification pass.
- [ ] Durable docs/contexts and tests are updated if classification changes.

<!-- coga:blackboard -->

Created under `cleanup-core-commands/` as part of the command-surface breakdown.
