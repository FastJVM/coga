---
title: 'Document the remedy for a bloated blackboard: sibling attachments and unattached
  contexts'
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

Dream 2026-W38 gap finding. Two marketing tickets independently solved the same problem the same way with no context to reach for: when the blackboard becomes the largest composed prompt layer, promote the task to directory form and move dated evidence into sibling attachments; move superseded program material into an unattached context. The architecture context only says the --prompt-report line is how a bloated blackboard gets noticed, not what to do next. Draft paragraph in Context.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
