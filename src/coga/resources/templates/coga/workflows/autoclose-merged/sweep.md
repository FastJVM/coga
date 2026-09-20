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
`branch:`, or a `worktree:` somebody still has to dispose of — it never removes
one itself, and Dream preserves the
source ticket until that human-typed retirement happens. Under this period task
the follow-ups are also recorded in the template's durable
`coga/recurring/<name>/retires.md`, keyed by slug and pruned of discharged
entries on every run, because this period task is deleted at the next period
boundary; the `coga/autoclose/sweep` skill owns those rules.
