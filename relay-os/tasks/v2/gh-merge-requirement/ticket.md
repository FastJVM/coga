---
slug: v2/gh-merge-requirement
title: gh-merge-requirement
status: active
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Cross-team work only becomes visible to other teammates once it's committed
and merged through a GitHub PR, which makes collaboration slow and serialized.
If the merge requirement / GitHub dependency were removed so that in-progress
work were automatically reviewable by other teammates, the workflow would be
much more efficient.

## Context

Touches relay's own merge/PR mechanism (nick's domain). This is a problem
statement, not a chosen solution — the `design` step should pin down what
"automatically reviewable without merging" means before any implementation.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
