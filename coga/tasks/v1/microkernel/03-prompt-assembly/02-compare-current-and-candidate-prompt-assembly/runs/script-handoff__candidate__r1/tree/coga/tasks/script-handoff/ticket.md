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

Verified `coga/tasks/script-handoff/prepared.txt` contains `prepared\n`; read the script note without rerunning `ticket.py`. Wrote `coga/tasks/script-handoff/result.txt` and read back exactly `ready\n` (one trailing newline). Script handoff preserved and published. No feature branch or PR is associated with this routine trial state. Write step complete; owner judgment remains.
