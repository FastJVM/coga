---
title: workflow-inline
status: in_progress
owner: trial-owner
agent: claude
contexts:
- trial/format
skills:
- trial/report
workflow:
  name: trial/inline
  steps:
  - name: write
    assignee: agent
  - name: judge
    assignee: owner
step: 2 (judge)
---

## Description

Write `ready` to sibling `result.txt`, verify it and finish this step.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

Wrote `coga/tasks/workflow-inline/result.txt` and read it back: exactly `ready` followed by one newline (`ready\n`, 6 bytes). Verification passed.

Checkout was clean on `main`; ticket is in progress at step 1 (write), with no recorded branch or PR. Local origin/main matched HEAD before editing. Ready for handoff.
