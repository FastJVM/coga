---
title: Packaged code workflows never name coga retire as the closing act
status: active
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
agent: claude
---

## Description

The review step of the packaged code/with-review workflow ends at autoclose and never tells the owner to run coga retire, so checkout-bearing done tickets pile up in consuming repos. Add the closing-act instruction to the packaged review sections so every installation gets it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
