---
title: workflow-skilled
status: in_progress
owner: trial-owner
agent: claude
contexts:
- trial/format
skills:
- trial/report
workflow:
  name: trial/skilled
  steps:
  - name: write
    assignee: agent
    skills:
    - trial/write
  - name: judge
    assignee: owner
step: 2 (judge)
---

## Description

Produce the result specified by the current step skill, verify it and finish this step.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

Wrote `coga/tasks/workflow-skilled/result.txt` and read it back: exact bytes `ready\n` (6 bytes), containing `ready` followed by one newline. Verification passed.

Checkout began clean on `main`; fetched and fast-forward checked local origin. No branch or PR is recorded; no implementation branch is needed for this task attachment. Write step complete and ready for handoff.
