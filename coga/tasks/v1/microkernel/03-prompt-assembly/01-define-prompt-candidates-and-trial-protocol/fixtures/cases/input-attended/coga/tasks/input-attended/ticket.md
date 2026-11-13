---
title: input-attended
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
step: 1 (write)
---

## Description

Write the owner-selected value to sibling `result.txt`. The required value has not been supplied. Do not guess it.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

No work performed yet.
