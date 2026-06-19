---
title: relay-uninstall
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Create a one-step command to uninstall Relay. "Relay-uninstall" removes all relay files from your machine. 

Having this in place will help folks try it when they know it's easily removed if they don't like it. 

## Context

