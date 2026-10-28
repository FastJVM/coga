---
title: Blackboard state cleanup
status: draft
owner: marc
agent: claude
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    assignee: agent
  - name: human-executes
    assignee: owner
  - name: verify-read-only
    assignee: agent
step: 1 (brief-and-hand-off)
---

## Description

Seeded example of Dream's owner-directed cleanup route.

validate-drift: large-blackboard

Use `coga validate --json` as the live member list. The owner chooses the
`coga/blackboard` remedy and publishes ticket and sibling-attachment changes
through `coga/state-publication`. This draft requires no branch or PR.

Close when the class is empty, or preserve an accepted-warning decision,
rationale, scope, and the same validator tag in its owning context first.

## Context

This fixture demonstrates the owner route without manufacturing an oversized
blackboard. Done tickets follow Dream's Retro/retirement split instead of
creating cleanup work.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
