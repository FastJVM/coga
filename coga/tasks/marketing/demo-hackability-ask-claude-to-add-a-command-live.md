---
title: 'Demo hackability: ask Claude to add a command live'
status: draft
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
---

## Description

Script and rehearse a short recorded demo where the presenter, inside `coga chat`, tells Claude "add this feature" and Claude adds a new working `coga` command entirely at the edge — no change under `src/coga/`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
