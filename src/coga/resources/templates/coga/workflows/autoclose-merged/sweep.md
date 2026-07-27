---
name: autoclose-merged/sweep
description: One-step lifecycle for the autoclose recurring recipe.
steps:
  - name: sweep
    skills:
      - coga/autoclose/sweep
    assignee: agent
---

## sweep

Recipe-backed recurring task. `coga recurring` runs `coga run autoclose`,
which calls `coga.autoclose.sweep_merged`: scan active and in-progress tickets, read
their `## Dev` `pr:` link, check GitHub merge state with `gh pr view`, and mark
only final-step or workflow-less tickets done when the linked PR has merged.
The command exits successfully when there is nothing to close.
