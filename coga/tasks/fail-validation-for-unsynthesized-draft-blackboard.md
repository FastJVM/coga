---
slug: fail-validation-for-unsynthesized-draft-blackboard
title: Fail validation for unsynthesized draft blackboards
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
- coga/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
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
