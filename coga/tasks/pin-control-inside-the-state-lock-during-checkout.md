---
title: Pin control inside the state lock during checkout preparation
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

`prepare_control_checkout` fetches and pins `origin/main` before taking `state_lock`, then reads local `main` inside the lock without re-pinning. A Coga publish that lands in between (push, then fast-forward of local `main`) makes local `main` look ahead of the stale pin. The realignment proof then runs against the stale pin and refuses with "local 'main' has commits not on origin/main (local Coga state commits are not yet on control: coga/log.md (lines not yet on control))", prescribing a `git pull --rebase` that was never needed. Fix it so a launch never refuses because control moved forward under it during preparation.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
