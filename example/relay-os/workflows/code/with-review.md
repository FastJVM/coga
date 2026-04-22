---
name: code/with-review
description: Standard code workflow with PR and approval gate.
steps:
  - name: implement
    skill: infra/testing-conventions
  - name: pr
  - name: approve
  - name: merge
---

## pr
Create a branch, push, open a PR. Title the PR after the task title.

## approve
Review the PR. If changes are needed, comment and wait. If approved, advance.

## merge
Merge the PR and clean up the branch.
