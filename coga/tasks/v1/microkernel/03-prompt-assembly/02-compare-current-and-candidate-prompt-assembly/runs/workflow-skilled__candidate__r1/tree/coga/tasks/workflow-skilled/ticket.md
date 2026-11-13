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

Completed write step using trial/write and trial/report.

- Output: `coga/tasks/workflow-skilled/result.txt`.
- Read-back evidence: exactly `ready` followed by one newline (`b'ready\n'`, 6 bytes).
- Checkout: clean `main` at start, current with local `origin/main`; no recorded feature branch or PR, and no pull-request refs on the isolated origin. This step changes task state only.
- Ready for the owner-held judge step; no unresolved blockers.
