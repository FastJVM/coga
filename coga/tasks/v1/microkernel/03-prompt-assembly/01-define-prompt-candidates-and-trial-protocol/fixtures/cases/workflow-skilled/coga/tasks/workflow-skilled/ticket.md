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
step: 1 (write)
---

## Description

Produce the result specified by the current step skill, verify it and finish this step.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

No work performed yet.
