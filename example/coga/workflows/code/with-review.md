---
name: code/with-review
description: Standard code workflow with PR and approval gate.
steps:
  - name: implement
    skills:
      - infra/testing-conventions
    assignee: agent
    requires: branch
  - name: pr
    assignee: agent
    requires: pr
  - name: approve
    assignee: owner
  - name: merge
    assignee: owner
---

## implement
From a clean `main`, create the feature branch, record it under `## Dev` as a
`branch:` line, and work on it in the same checkout; push it and return to
`main` before bumping. `requires: branch` refuses the bump until the line is
present in the ticket copy of the checkout you bump from.

## pr
Push the recorded branch and open a PR. Title the PR after the task title.

## approve
Review the PR. If changes are needed, comment and wait. If approved, advance.

## merge
Merge the PR and clean up the branch.
