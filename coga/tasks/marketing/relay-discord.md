---
slug: marketing/relay-discord
title: relay-discord
status: active
mode: llm
owner: zach
human: zach
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: autonomy/human-only
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: human
  - name: verify-read-only
    skills: []
    assignee: agent
step: 1 (brief-and-hand-off)
---

## Description

Create a Relay Discord for discussion, questions, and contributions from interested users.

Set up basic channels (#help, #contributing, #general) and link it prominently from the README.

Post a monthly changelog there as the regular public update. (#announcements) (I suppose this could also be part of relay-recurring)

Rollout (added 2026-06-12): add the Discord invite to the README, make the
relay repo public, and tell our users/friends about it. Repo-public is the
prerequisite for the other two.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
