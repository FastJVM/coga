---
slug: v2/issue-inbox-slack
title: issue-inbox-slack
status: paused
mode: llm
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

Enrich Relay's existing Slack posts into an inbox: panics carry the blocker reason and required action, dones carry the outcome — readable without opening a terminal.
Every post links the next step: the relay command to run or a link to the ticket file.
Webhook-only; no Slack app, no buttons, no server.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
