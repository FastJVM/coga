---
slug: declined-dream-finding
title: Declined Dream finding
status: canceled
owner: marc
human: marc
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - infra/testing-conventions
    assignee: agent
  - name: pr
    skills: []
    assignee: agent
  - name: approve
    skills: []
    assignee: human
  - name: merge
    skills: []
    assignee: owner
secrets: null
script: null
---

## Description

Seeded example of a Dream finding that was intentionally declined rather than
reported as completed work.

## Context

Cancellation is terminal and clears the workflow step. Its required reason
lives in the append-only audit log, while this ticket remains ordinary,
human-readable markdown.

<!-- coga:blackboard -->

# Declined Dream finding

The blackboard is a notepad to be written to often as the human and agent
works through a task.
