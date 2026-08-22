---
name: autoclose-merged/sweep
description: One-step lifecycle for the autoclose recurring task's deterministic half.
steps:
  - name: sweep
    skills:
      - coga/autoclose/sweep
    assignee: agent
---

## sweep

Script-backed recurring task. `coga launch` runs the period task's reserved
`ticket.py`, which calls `coga.autoclose.sweep_merged`: scan active and
in-progress tickets, read
their `## Dev` `pr:` link, check GitHub merge state with `gh pr view`, and mark
only final-step or workflow-less tickets done when the linked PR has merged.
The command exits successfully when there is nothing to close. It then names
the `coga retire` follow-up for each closed ticket that still records a
`branch:` or `worktree:` — it never removes one itself, and Dream preserves the
source ticket until that human-typed retirement happens.
