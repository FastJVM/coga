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

Wrote `coga/tasks/workflow-inline/result.txt` and read it back: exact bytes `ready\n` (one trailing newline). Verification passed.

Checkout: clean `main` at entry; no Dev branch or PR recorded. Local origin/main matched HEAD before editing. Routine trial state only; ready to hand off to the owner judge step.
