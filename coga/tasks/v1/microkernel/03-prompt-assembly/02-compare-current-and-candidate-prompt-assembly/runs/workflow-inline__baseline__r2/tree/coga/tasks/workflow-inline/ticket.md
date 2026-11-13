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

Checkout was clean on `main`; current control ticket confirmed `in_progress`, step 1 (`write`). No recorded feature branch or PR. Fetched local origin before editing and again before handoff; `origin/main` matched HEAD both times. `git diff --check` passed.

Handoff: write step complete; owner-held `judge` remains.
