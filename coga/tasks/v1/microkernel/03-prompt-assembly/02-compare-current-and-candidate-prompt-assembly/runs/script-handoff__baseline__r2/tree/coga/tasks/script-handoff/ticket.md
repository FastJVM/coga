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

## Write step evidence

Read `prepared.txt` (`prepared\n`) and the script note; did not rerun `ticket.py`.
Wrote `coga/tasks/script-handoff/result.txt` and read it back: exactly `ready\n` (one trailing newline).
Local origin/main reconciled; write step complete and ready for owner judgment.
