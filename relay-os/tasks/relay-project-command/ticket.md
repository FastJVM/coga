---
title: relay-project-command
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
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

Build a project command in Relay. "Relay project" interviews a human about a project--goal, scope, constraints, acceptance criteria--through a short series of questions. 

From the answers, it creates an ordered set of draft tickets, one per each step. 

It can also seed the interview from an existing vision doc instead of starting from scratch (covers the deleted vision-to-plan ticket).

## Context

