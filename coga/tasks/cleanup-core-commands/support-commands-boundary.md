---
slug: cleanup-core-commands/support-commands-boundary
title: Classify support commands under the small-core rule
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

Classify support and bootstrap-adjacent commands under the small-core rule and
move any command behavior that clearly belongs in a ticket/workflow/script
shape. Commands in scope: `coga secret get`, `coga uninstall`, package upgrade
or refresh documentation, and any installer/bootstrap command surface that
remains after excluding `create`, `launch` substrate, and `skill *`.

This ticket exists so support commands do not slip through the audit merely
because they are not obvious project/workflow commands. Some may stay external
tooling or installer substrate; the point is to prove that explicitly.

## Context

Directory index: `cleanup-core-commands/README`.

Owner direction: except for `skill *`, `create`, and the true launch executor
substrate, commands should be treated as candidates to leave the core command
surface. Be careful with secrets: secret values must never be written into
tickets, prompts, blackboards, logs, or sync commits. A ticket-shaped secret
operation can record intent and outcome, but not secret material.

There is no top-level `coga update` command in this checkout; do not invent one
in this ticket. If an update-like surface is needed, clarify whether the target
is package upgrade documentation, fresh `init`, or `coga skill update` (which is
excluded with `skill *` unless the owner changes that direction).

Design first. Decide whether each support command is:

- installer/bootstrap substrate that cannot require an existing ticket;
- external/script tooling that should stay outside ticket lifecycle;
- ticket/workflow operation with persisted intent/outcome;
- thin compatibility alias.

## Acceptance Criteria

- [ ] `secret get`, `uninstall`, package upgrade/refresh docs, and related support surfaces are
      classified under the new small-core rule.
- [ ] Any moved support behavior preserves security boundaries, especially for
      secret values.
- [ ] Commands that stay outside tickets have a documented substrate or external
      tooling reason, not an implicit "already exists" reason.
- [ ] Follow-up tickets are created for migrations that need a new mechanism.
- [ ] Durable docs/contexts and tests are updated for any behavior change.

<!-- coga:blackboard -->

Created under `cleanup-core-commands/` as part of the command-surface breakdown.
