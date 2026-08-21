---
slug: auto/deterministic-repo-check
title: Run a deterministic repository check
status: active
owner: marc
human: marc
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: deterministic/check
  steps:
  - name: execute
    skills: []
    assignee: agent
step: 1 (execute)
secrets: null
---

## Description

Seeded example of a ticket with a deterministic half. The reserved
`ticket.py` sibling appends one visible result to this blackboard and completes
the one-step workflow without composing a prompt or launching an agent.

## Context

Any other Python attachment remains an ordinary attachment. Only the exact
`ticket.py` sibling name participates in launch dispatch.

<!-- coga:blackboard -->

# Deterministic repository check
