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
step: 2 (judge)
---

## Description

Write the owner-selected value to sibling `result.txt`. The required value has not been supplied. Do not guess it.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

Owner selected `approved`. Wrote `coga/tasks/input-attended/result.txt` and read it back: exactly `approved` followed by one newline. Write step complete; ready for owner judgment.
