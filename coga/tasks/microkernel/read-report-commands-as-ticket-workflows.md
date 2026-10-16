---
title: Classify read and report commands under the small-core rule
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga/principles
  - coga/tickets
  - coga/lifecycle
  - coga/usage
  - coga/recurring
  - coga/codebase
  - coga/testing
  - coga/current-direction
  - coga/extension-model
  - coga/project-stage
  - coga/cli
  - dev/checkouts
workflow: code/design-then-implement
---

## Description

Settle the placement of the read/report heads: `coga show`, `coga status`,
`coga validate`, `coga usage`, and `coga recurring list`. Keep shared
rendering (`coga.views`) and validation infrastructure in core where they have
two or more consumers. Decide for each head whether it is a thin read-view
wrapper with a co-versioning proof, an edge command, or alias sugar.

Preserve quick read ergonomics and machine-readable output (`--json`).

### Acceptance criteria

- [ ] Each head is classified as edge command, read-view wrapper with a
      written co-versioning proof, or alias sugar, and recorded in
      `coga/extension-model` (both copies).
- [ ] Reusable render/check/report logic moves out of command files only
      where an existing edge shape supports it without hidden transient
      parameters.
- [ ] `validate` stays fail-loud with stable exit codes and JSON for
      automation (Dream, CI, `coga launch` preflights).
- [ ] `launch --prompt-report` gets its home decided here, as handed off by
      `microkernel/launch-decomposition`.
- [ ] The row leaves the "Open command placements" table; tests and the
      `coga/cli` index are updated.

## Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

`show` and `status` already render through `coga.views`; verify the current
split before moving anything. A parameterized read must not smuggle hidden
launch-time input into a ticket: if a head keeps a tiny Typer layer to pass a
display parameter, say why and keep the substance outside the command file.

### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{show,status,validate,usage,recurring}.py`.
- Surfaces resolve; the old pointer to the pre-split extension-model table now
  lives in `docs/archive/cli-extension-audit.md`.
- Not delivered: the row is open in extension-model.

<!-- coga:blackboard -->

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
