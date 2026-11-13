---
name: trial/inline
description: Trial output followed by owner judgment.
steps:
  - name: write
    assignee: agent
  - name: judge
    assignee: owner
---

## write

Write the value requested by the ticket to its sibling `result.txt`. Read it back.

## judge

The owner judges the result. An assist only inspects/reports unless the owner explicitly requests advancement.
