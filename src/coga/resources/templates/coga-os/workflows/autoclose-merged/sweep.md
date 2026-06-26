---
name: autoclose-merged/sweep
description: One-step script workflow that closes final-step Coga tickets whose linked PR has merged.
steps:
  - name: sweep
    skills:
      - coga/autoclose/sweep
    assignee: agent
---

## sweep

Script step. Runs `coga/autoclose/sweep`, which calls
`coga.autoclose.sweep_merged`: scan active and in-progress tickets, read
their `## Dev` `pr:` link, check GitHub merge state with `gh pr view`, and mark
only final-step or workflow-less tickets done when the linked PR has merged.
The command exits successfully when there is nothing to close.
