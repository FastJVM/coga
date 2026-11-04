---
name: phone-home/run
description: Deterministic weekly usage snapshot.
steps:
  - name: send
    skills: []
    assignee: agent
---

## send

The reserved `ticket.py` sends the snapshot and bumps through the CLI.

## No other-agent code review

This is the one-step lifecycle of a recurring task's deterministic
half. It produces no code, so no `other-agent` step reviews it.
