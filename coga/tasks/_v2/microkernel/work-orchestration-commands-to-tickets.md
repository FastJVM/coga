---
title: Move work orchestration commands to tickets
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga-dev/principles
  - coga/megalaunch
  - coga/checkout-cleanup
  - coga/notifications
  - coga/recurring/scheduling
  - coga-dev/codebase
  - coga-dev/testing
  - coga-dev/current-direction
  - coga-dev/microkernel
  - coga-dev/project-stage
  - coga/cli
  - coga/checkouts
workflow: code/design-then-implement
---

## Description

Settle the placement of the in-package heads that orchestrate work:
`coga retire`, `coga megalaunch` (and its `pick` alias), and `coga slack`.
Move each head's single-consumer substance to the edge (command ticket,
`ticket.py`, `src/coga_edge/`) behind a thin creator/launcher/alias, or
record why it must be co-versioned with the package.

### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      simplify duplicated launch/orchestration scaffolding and unnecessary
      wrappers in `megalaunch` and `slack` using the shared launch boundary.
      Count their edge implementations in the before/after total; moving
      queue policy out of core alone is a placement gain, not less code to
      maintain. Keep recurring recipes and the executor outside this scope.

- [ ] The design defines one shared creator/launcher/alias pattern for these
      heads, so they do not each invent a migration shape.
- [x] `retire` is split into a concrete follow-up with exact acceptance
      criteria: `microkernel/move-retire-to-a-command-ticket` (2026-10-16).
      Its state rule stays: a canceled ticket gets a retire task; a done
      ticket is deleted in place.
- [ ] `megalaunch` and `slack` are each moved or given a co-versioning proof
      in `coga-dev/microkernel`. Megalaunch's queue selection, liveness
      defaults and timeout classification are caller policy, not executor
      substrate.
- [ ] Implementation is split per command shape after design review.
- [ ] Human-visible side effects stay durable (blackboards, `coga/log.md`,
      sync commits, notifications).
- [ ] The three heads leave (retire through its follow-up) the "Open command placements" table (both
      copies); `coga/megalaunch`, `coga/checkout-cleanup`,
      `coga/notifications` and the `coga/cli` index match; tests pass.
      Retire's exit is implemented on branch `retire-command-ticket`
      (`microkernel/move-retire-to-a-command-ticket`, pending review and
      merge): the row there names only `megalaunch`, `slack`.

## Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

Prior art: `ticket` (command head plus `bootstrap/ticket` and
`coga.authoring` finalize), `bootstrap/recurring-scan`, the `delete-task`
recipe, `bootstrap/resolve-conflicts` and `bootstrap/address-pr-comments`
command tickets reached by aliases.

Depends on `_v2/microkernel/launch-decomposition` for a public
one-session API (megalaunch currently imports the session runner out of
`commands/launch.py`). Does not touch `runner.RECIPES`: that registry is
owned by `_v2/gigantic-refactor-move-recurring-recipes-out-of-co`.

Out of scope: `skill *`, `create`, the launch executor, recurring recipes.

### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{retire,megalaunch,slack}.py`,
  `src/coga/megalaunch.py`.
- Stale surfaces removed (Dream W39 F47): `coga digest` (removed by
  `remov-digest-in-recurring`) and `coga project` (removed by
  `remove-coga-build-and-project`). Bare `coga recurring` is already a thin
  head over the `recurring-scan` recipe, so recurring maintenance left scope.
- Not delivered: all three heads are still listed in extension-model's
  "Open command placements".

Previous ref: `microkernel/work-orchestration-commands-to-tickets` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

<!-- coga:blackboard -->

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
