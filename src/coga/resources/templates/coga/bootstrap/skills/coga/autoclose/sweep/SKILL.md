---
name: coga/autoclose/sweep
description: Close final-step Coga tickets whose linked GitHub PR has merged.
script: run.py
---

# Autoclose Merged Tickets

This skill is the script body of the `recurring/autoclose-merged/`
ticket. It runs the merged-ticket auto-close sweep — the sole trigger for closing
tickets whose PR has merged:

1. scan active and in-progress tickets,
2. read each ticket blackboard's `## Dev` `pr:` link,
3. check the linked PR state with `gh pr view`, and
4. mark the ticket `done` only when it is on its final workflow step, or has no
   workflow, and the PR is merged.

The scope is defined by `coga.autoclose.sweep_merged`.
Mid-workflow merges stay untouched because they are suspicious and need a human
to finish the ticket explicitly.

The script imports `coga.autoclose.sweep_merged` and calls it directly, so
it does not depend on `coga` being on `PATH` inside the script environment.
`gh` failures and task validation failures are hard failures, matching the
manual command's behavior.
