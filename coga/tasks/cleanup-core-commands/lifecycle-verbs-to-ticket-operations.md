---
slug: cleanup-core-commands/lifecycle-verbs-to-ticket-operations
title: Move lifecycle verbs to ticket operations
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

Move the user-facing lifecycle verbs out of the protected core command surface.
The commands in scope are `coga mark active`, `coga mark paused`,
`coga mark done`, `coga bump`, `coga block`, and `coga unblock`.

The desired product shape is that lifecycle changes are ticket/session
operations over a small internal state-write primitive, not independent core
verbs that make task state feel separate from the workflow that owns it. The
primitive may remain in Python if tickets and scripts need it to advance safely;
the command surface should become as small and ticket-shaped as possible.

## Context

Directory index: `cleanup-core-commands/README`.

Owner direction from the parent: only `create` is presumed irreducibly core.
Everything else should be treated as a ticket/workflow/script candidate unless
the implementation proves a specific bootstrapping exception. This ticket tests
that rule on the lifecycle verbs first because they currently look core only
because `launch` calls the same state-transition machinery.

Design first. Identify:

- Which internal state-write functions must stay as substrate.
- Which user-facing lifecycle commands can become workflow/script operations.
- How supervised agent sessions advance without telling humans to run a
  separate command manually.
- How Slack/git sync/logging stay fail-loud and recoverable.
- What compatibility aliases, if any, should remain as thin sugar.

Out of scope: changing `create`, changing skill installation, and decomposing
the launch executor itself. If launch must grow a new hook to run lifecycle
operations, record that dependency and coordinate with
`cleanup-core-commands/launch-decomposition`.

## Acceptance Criteria

- [ ] The design step documents the minimal internal state-write substrate and
      separates it from user-facing lifecycle verbs.
- [ ] `mark`, `bump`, `block`, and `unblock` are either moved to ticket/script
      operations or each has a precise follow-up explaining what mechanism is
      missing.
- [ ] If the design touches both state writes and blocker handling, split the
      implementation into smaller follow-up tickets before code changes.
- [ ] Existing lifecycle invariants are preserved: status transitions, step
      transitions, blocking/unblocking semantics, logging, git sync, and
      notifications.
- [ ] Tests cover the changed lifecycle behavior and compatibility surface.
- [ ] `coga/extension-model`, `coga/cli`, and packaged context copies are updated
      when the command boundary changes.

<!-- coga:blackboard -->

Created under `cleanup-core-commands/` as part of the command-surface breakdown.
