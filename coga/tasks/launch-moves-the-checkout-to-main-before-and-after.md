---
title: Launch moves the checkout to main before and after a ticket session
status: draft
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
---

## Description

Ticket launches (not bootstrap or chat targets) should bring the checkout to a clean, current main on their own before the agent starts, and again after the session ends, instead of relying on each agent to run the dev/checkouts start and end procedure. Today a session that ends on a feature branch (for example a bootstrap/orient chat) leaves the next launch starting there. Bootstrap and chat sessions may keep working from whatever branch they start on.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
