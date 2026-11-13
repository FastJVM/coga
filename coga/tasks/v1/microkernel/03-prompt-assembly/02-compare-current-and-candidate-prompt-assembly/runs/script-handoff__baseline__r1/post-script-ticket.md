---
title: script-handoff
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

Read sibling `prepared.txt` and the script note, then write `ready` to sibling `result.txt`, verify and finish this step. Do not rerun ticket.py.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

Script phase succeeded once; prepared.txt contains prepared. Agent work remains in this step.
