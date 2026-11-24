---
name: code/with-review
description: Code changes with deterministic Git steps and an owner review.
steps:
  - name: open-branch
    run: git/open-branch
    assignee: agent
    requires: branch
  - name: implement
    skills:
      - infra/testing-conventions
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
      - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    run: git/push-and-open-pr
    assignee: agent
    requires: pr
  - name: review
    assignee: owner
---

## review

Review the PR and record completion on the branch before merging.
