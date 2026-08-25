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
    assignee: human
  - name: merge
    assignee: owner
---

## implement
Create the feature branch and its checkout, then record both under `## Dev` as
`branch:` and `worktree:` lines. `requires: branch` refuses the bump until they
are present in the ticket copy of the checkout you bump from.

## pr
Push the recorded branch and open a PR. Title the PR after the task title.

## approve
Review the PR. If changes are needed, comment and wait. If approved, advance.

## merge
Merge the PR and clean up the branch.
