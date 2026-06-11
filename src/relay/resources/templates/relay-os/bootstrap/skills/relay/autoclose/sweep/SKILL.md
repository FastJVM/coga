---
name: relay/autoclose/sweep
description: Close final-step Relay tickets whose linked GitHub PR has merged.
script: run.py
---

# Autoclose Merged Tickets

This skill is the `mode: script` body of the `recurring/autoclose-merged/`
ticket. It runs the same merged-ticket sweep as the manual `relay automerge`
command:

1. scan active and in-progress tickets,
2. read each ticket blackboard's `## Dev` `pr:` link,
3. check the linked PR state with `gh pr view`, and
4. mark the ticket `done` only when it is on its final workflow step, or has no
   workflow, and the PR is merged.

The scope is intentionally identical to `relay.automerge.auto_bump_merged`.
Mid-workflow merges stay untouched because they are suspicious and need a human
to finish the ticket explicitly.

The script imports `relay.automerge.auto_bump_merged` and calls it directly, so
it does not depend on `relay` being on `PATH` inside the script environment.
`gh` failures and task validation failures are hard failures, matching the
manual command's behavior.
