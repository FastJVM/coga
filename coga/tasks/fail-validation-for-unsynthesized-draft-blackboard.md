---
slug: fail-validation-for-unsynthesized-draft-blackboard
title: Fail validation for unsynthesized draft blackboards
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
  - dev/code
  - coga/codebase
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Make `coga validate` treat an unsynthesized draft blackboard as an error rather
than a warning. A draft with authoring or evaluator residue cannot be activated
or launched, so validation must exit nonzero and tell the ticket writer to fold
durable content into the ticket body.

## Context

The existing `unsynthesized-draft-blackboard` check and activation gate already
detect the right condition. Preserve the `## Production notes` escape hatch and
the separate size-based blackboard warning; only promote the readiness issue's
severity. Update focused tests and the live and packaged behavioral docs.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: codex/fail-unsynthesized-draft-validation
worktree: /tmp/coga-fail-unsynthesized-draft-validation
pr: https://github.com/FastJVM/coga/pull/611
