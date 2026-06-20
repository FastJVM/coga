---
name: autoclose-merged/sweep
description: One-step script workflow that closes final-step Relay tickets whose linked PR has merged.
steps:
  - name: sweep
    skills:
      - relay/autoclose/sweep
    assignee: agent
---

## sweep

Script step. Runs `relay/autoclose/sweep`, which calls
`relay.autoclose.sweep_merged`: scan active and in-progress tickets, read
their `## Dev` `pr:` link, check GitHub merge state with `gh pr view`, and mark
only final-step or workflow-less tickets done when the linked PR has merged.
The command exits successfully when there is nothing to close.
