---
title: Install smoke CI matrix
status: draft
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

Add a GitHub Actions install-smoke matrix (ubuntu, macos, windows × Python
3.11) that installs the built wheel and runs `coga --version`, `coga init` on
a scratch repo, and `coga validate`, so installer regressions are caught on
every PR. Done means the workflow is merged and green on `main`. Runners have
no authenticated agent CLI, so the matrix stops before `coga launch` (for
example at `coga launch <slug> --prompt-report`).

## Context

Deferred from the V1 `marketing/fix-installer/` set, which uses Docker and AWS
machines instead. Reuse that set's install/walk script. The existing
`.github/workflows/release.yml` only builds and publishes. Cited topics:
`coga/install`, `coga/testing`, `coga/releasing`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
