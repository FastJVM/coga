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

Wrote `coga/tasks/workflow-skilled/result.txt`. Read back and verified exact content `ready\n` (6 bytes: `ready` followed by one newline).

Checkout started clean on `main`; fetched local origin and confirmed the control ticket is in progress at `write`. No feature branch or PR is recorded; this task attachment is routine Coga state. Ready for owner judgment after the write-step handoff.
