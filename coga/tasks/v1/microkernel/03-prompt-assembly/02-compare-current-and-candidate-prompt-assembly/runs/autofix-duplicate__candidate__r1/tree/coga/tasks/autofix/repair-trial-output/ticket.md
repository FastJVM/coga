---
title: Create the trial output directory before writing
status: active
owner: trial-owner
agent: claude
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

Repair recurring/trial: ticket.py exits 7 because the output directory is absent. Create it before writing and retain visible failures.

<!-- coga:blackboard -->

## Notes

Existing known issue.
