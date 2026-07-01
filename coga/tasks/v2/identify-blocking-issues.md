---
slug: v2/identify-blocking-issues
title: identify-blocking-issues
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

When relay project creates an ordered list of steps, if say step 3's completion relies on dependencies that get created in step 5, there should be a way to identify that. 

There could possibly be another field in the ticket labelled "dependencies" and it lists the title of the ticket it needs completed before it's able to be finished. 

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
