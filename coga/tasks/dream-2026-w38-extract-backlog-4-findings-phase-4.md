---
title: 'Dream 2026-W38 extract backlog: 4 findings Phase 4 could not consume'
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

Carrier ticket. Dream 2026-W38's knowledge scan classified four findings as extract, but every source ticket carries a real ## Dev branch and worktree (retirement debt, deliberately left on disk so the human-typed coga retire <slug> stays valid), so Phase 4 could not consume them. The full finding paragraphs are in this ticket's Context so they survive the Dream task's retirement.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
