---
title: Classify residual command surfaces
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga-dev/principles
  - coga/init
  - coga/tickets
  - coga/skill-management
  - coga/recurring/scheduling
  - dev/checkout-cleanup
  - coga-dev/codebase
  - coga-dev/testing
  - coga-dev/current-direction
  - coga-dev/microkernel
  - coga-dev/project-stage
  - coga/cli
  - dev/checkouts
workflow: code/design-then-implement
---

## Description

Close the two residual rows of the "Open command placements" table:

- **`coga ticket`**: write the co-versioning proof for its current head, or
  move it to the edge. The current split is the `bootstrap/ticket` interview
  target, `coga.authoring` finalize (validation and sync after the agent
  exits), and `commands/ticket.py`, the argument-to-draft coordinator that
  calls finalize inline. A plain `launch bootstrap/ticket` alias cannot
  replace it because the head drafts a ticket on the fly and owns the
  post-exit phase.
- **`skill *`**: record its explicit classification as a thin wrapper over
  `gh skill`, either external tooling (extractable as a `gh` extension) or
  a co-versioned package command, with the owner direction recorded.

### Acceptance criteria

- [ ] `ticket` has a written co-versioning proof in `coga-dev/microkernel`,
      or is moved to the edge with unchanged behavior and tests.
- [ ] `skill *` has an explicit classification and reason in
      `coga-dev/microkernel`.
- [ ] Both rows leave the local-only `coga-dev/microkernel` table;
      `docs/archive/cli-extension-audit.md`, `coga/tickets/authoring`,
      `coga/skill-management` and the `coga/cli` index match.
- [ ] Any migration found here becomes its own follow-up ticket.

## Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

Already settled and out of scope (Dream W39 F48): default aliases are argv
sugar; fresh `init` is kernel; `delete` is a thin head over the `delete-task`
recipe; bare `recurring` is a thin head over `recurring-scan`.

### Premise check (2026-10-16, pull-forward to v1)

- Delivered in part (Dream W39 F48): aliases, `init`, `delete`, bare
  `recurring` are classified in extension-model and the audit. Scope narrowed
  to `ticket` and `skill *`, the two surfaces still in the open table.

<!-- coga:blackboard -->

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
