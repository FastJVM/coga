---
title: Weekly Coga usage snapshot
status: active
owner: nicktoper
agent: claude
contexts:
- coga/telemetry
- coga/period-task
period_generation: b37c034f-65cb-4b15-a03f-37c913bd9134
workflow:
  name: phone-home/run
  steps:
  - name: send
    skills: []
    assignee: agent
step: 1 (send)
---

## Description

Attempt one weekly usage snapshot from the sibling `ticket.py`, without an
agent. See `coga/telemetry` for the data boundary, opt-out, and loss semantics.
Coga installs no scheduler. This measures repos with active sweeps, not installs.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
