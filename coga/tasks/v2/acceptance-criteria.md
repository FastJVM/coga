---
slug: v2/acceptance-criteria
title: acceptance-criteria
status: paused
autonomy: interactive
owner: zach
human: zach
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

Create an acceptance criteria spot on relay tickets. The relay ticket interviewer should also have a question regarding the acceptance criteria (or the definition of done)

Possibly have a way to set acceptance criteria on relay create (ie relay create make-ticket -ac1 "create the ticket" --ac2 "commit the ticket" 

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
