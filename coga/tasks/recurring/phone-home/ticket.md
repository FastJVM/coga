---
title: Weekly Coga usage snapshot
status: done
owner: nicktoper
agent: claude
contexts:
- coga/telemetry
- coga/period-task
period_generation: 52a5bb9a-ecb9-4cb2-a2b2-247c2576142b
workflow:
  name: phone-home/run
  steps:
  - name: send
    skills: []
    assignee: agent
---

## Description

Attempt one weekly usage snapshot from the sibling `ticket.py`, without an
agent. See `coga/telemetry` for the data boundary, opt-out, and loss semantics.
Coga installs no scheduler. This measures repos with active sweeps, not installs.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Phone home

Run 3: capture suppressed; receipt suppressed.
