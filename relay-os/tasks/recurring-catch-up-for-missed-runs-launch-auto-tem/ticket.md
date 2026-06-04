---
title: 'recurring: catch-up for missed runs + launch auto templates interactively'
status: draft
mode: interactive
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
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description



## Context

