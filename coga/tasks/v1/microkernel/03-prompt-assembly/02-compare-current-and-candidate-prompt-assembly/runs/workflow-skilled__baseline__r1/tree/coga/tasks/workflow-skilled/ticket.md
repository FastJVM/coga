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

Wrote `coga/tasks/workflow-skilled/result.txt`. Read back and verified exact content `ready\n` (6 bytes: the value `ready` followed by one newline).

Checkout: clean `main` at start; control-copy ticket confirmed `in_progress`, step `write`, with no recorded branch or PR. This is routine trial state under the Coga root; no code branch or PR is needed. Fetched local `origin/main` before editing; no drift. Result is ready for the owner-held `judge` step.
