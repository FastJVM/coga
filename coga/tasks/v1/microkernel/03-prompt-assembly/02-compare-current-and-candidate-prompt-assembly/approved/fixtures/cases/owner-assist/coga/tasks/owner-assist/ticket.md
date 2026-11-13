---
title: owner-assist
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

Inspect sibling `result.txt` and report whether it contains `ready` and a newline. Do not advance without the owner asking.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

No work performed yet.
