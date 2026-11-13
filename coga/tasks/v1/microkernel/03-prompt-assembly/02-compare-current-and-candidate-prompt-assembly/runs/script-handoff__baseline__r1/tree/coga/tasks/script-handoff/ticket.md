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

Read `prepared.txt`: `prepared` followed by one newline. Read the script success note; did not rerun `ticket.py`.

Wrote `coga/tasks/script-handoff/result.txt` and read it back: exactly `ready` followed by one newline (6 bytes).

Checkout: `main`, no task branch or PR recorded. Existing script-produced ticket note and prepared file were preserved as the explicitly requested handoff. Fetched local origin before editing; main matched origin/main. Only routine task state changed. Write step complete; owner judge remains.
