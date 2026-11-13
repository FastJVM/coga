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

Wrote `coga/tasks/workflow-inline/result.txt` and read it back. Observed exact bytes: `ready\n` (the value `ready` followed by one newline). Verification passed.

Checkout was clean on `main`; local `origin/main` matched HEAD before editing. The control-copy ticket was `in_progress`, step `1 (write)`, with no recorded branch or PR. No PR merge status applies in this isolated local-origin trial.
