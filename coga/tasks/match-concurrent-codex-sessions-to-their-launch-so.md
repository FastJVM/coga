---
title: Match concurrent Codex sessions to their launch so usage stops undercounting
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

coga usage reports 20 of 55 Codex sessions last week (Sep 28 - Oct 4) as unknown; their real tokens are about 43% of Codex usage. Give every agent launch a unique marker in the composed prompt and use it to pick the right transcript when several match.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
