---
name: coga/autoclose/sweep
description: Close final-step Coga tickets whose linked GitHub PR has merged.
---

# Autoclose Merged Tickets

This skill documents the `autoclose` recipe used by the
`recurring/autoclose-merged/` ticket. The recipe runs the merged-ticket
auto-close sweep — the sole trigger for closing
tickets whose PR has merged:

1. scan active and in-progress tickets,
2. read each ticket blackboard's `## Dev` `pr:` link,
3. check the linked PR state with `gh pr view`, and
4. mark the ticket `done` only when it is on its final workflow step, or has no
   workflow, and the PR is merged.

The scope is defined by `coga.autoclose.sweep_merged`.
Mid-workflow merges stay untouched because they are suspicious and need a human
to finish the ticket explicitly.

Run it directly with `coga run autoclose`. `gh` failures and task validation
failures are hard failures.
