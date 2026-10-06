---
title: Declined Dream finding
status: canceled
owner: marc
agent: claude
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
    assignee: owner
  - name: merge
    skills: []
    assignee: owner
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

## Dev

branch: declined-dream-prototype
branch: declined-dream-earlier-attempt

Both branches are explicit ownership records. A closed PR alone would not
permit their deletion; terminal ownership, PR-head checks, archival, and
checkout safety must all pass. Cleanup preserves any branch another live
ticket records. These fixture names have no real Git refs.
