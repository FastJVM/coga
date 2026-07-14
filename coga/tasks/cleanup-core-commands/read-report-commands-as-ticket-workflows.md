---
slug: cleanup-core-commands/read-report-commands-as-ticket-workflows
title: Classify read and report commands under the small-core rule
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

Classify read/report command behavior under the small-core rule, then move only
the pieces whose ticket-shaped or script-shaped home is clear. Commands in
scope: `coga show`, `coga status`, `coga validate`, `coga usage`, and
`coga recurring list`.

The target is not ceremony for its own sake. Preserve quick read ergonomics, but
move reusable render/check/report logic into editable skills, workflows, or
script-shaped modules where that makes the command surface smaller and more
legible.

## Context

Directory index: `cleanup-core-commands/README`.

`show` and `status` have already had render substance collapsed toward
`coga.views` / `coga/show` according to `coga/extension-model`; verify the
current state before changing them. This ticket should classify the remaining
read/report commands under the new smaller-core rule and migrate only the cases
with a clear shape.

Important constraint: parameterized reads must not smuggle hidden launch-time
input into a ticket. If a command keeps a tiny Typer head to materialize a ref
or pass a transient display parameter, explain why and keep the reusable
substance outside the command file.

## Acceptance Criteria

- [ ] Each command in scope is classified as ticket workflow, bootstrap script,
      read-view wrapper, or explicit keep-command exception.
- [ ] Reusable render/check/report logic is moved out of command files only
      where an existing script/workflow shape supports it without adding
      ceremony or hidden transient parameters.
- [ ] Quick read ergonomics are preserved or replaced with documented alias
      sugar.
- [ ] Validation failures remain fail-loud and suitable for automation.
- [ ] Tests and durable command-reference contexts are updated.

<!-- coga:blackboard -->

Created under `cleanup-core-commands/` as part of the command-surface breakdown.
