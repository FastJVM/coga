---
title: Legacy Dream
status: paused
step: 1
period_generation: fixture-generation
workflow:
  name: direct/body
  steps:
    - name: body
      assignee: agent
---

## Description

Unrelated instructions must survive.

### Phase 1 — validate-drift

Read `bootstrap/dream/tasks/validate-drift`, then run
`coga run validate-drift`. The recipe runs the same deterministic surface as
`coga validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to this task's blackboard.

### Phase 5 — cleanup-orphan-markers

Read `bootstrap/dream/tasks/cleanup-orphan-markers`, then run
`coga run cleanup-orphan-markers`. The recipe detects cleanup candidates and
gates deletion through `bootstrap/delete-task` (`coga run delete-task`). That
delete surface ships, but until its cleanup PR-dispatch wiring is finished the
recipe reports `human-needed` and deletes nothing.

Keep the rest of this body unchanged.

<!-- coga:blackboard -->

Preserve this period's findings.
