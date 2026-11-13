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
step: 2 (judge)
---

## Description

Read sibling `prepared.txt` and the script note, then write `ready` to sibling `result.txt`, verify and finish this step. Do not rerun ticket.py.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

Script phase succeeded once; prepared.txt contains prepared. Agent work remains in this step.

Verified `coga/tasks/script-handoff/result.txt` contains exactly `ready` followed by one newline (read back as `b'ready\n'`). Read prepared.txt (`prepared` plus newline) and the script note; did not rerun ticket.py. Existing script state preserved and published. Working on main; no task branch or PR is recorded, so no PR merge status applies.
