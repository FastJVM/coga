---
name: code/with-review
description: Standard code workflow with PR and approval gate. Use for changes that need a second set of eyes before landing.
steps:
  - name: implement
    skill: infra/testing-conventions
  - name: pr
  - name: approve
  - name: merge
---

## pr

Create a feature branch, push it, and open a pull request against
`main`. Include a short description of what changed and why. Link the
task ID in the PR body.

## approve

Wait for a human reviewer to approve the PR. This step does not
self-advance — a human calls `relay step` after they've reviewed and
approved.

## merge

Merge the PR with the default merge strategy for the repo. Delete the
feature branch afterwards. Post a `relay feed` noting the merged SHA.
