---
slug: marketing/relay-discord
title: relay-discord
status: paused
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
  - marketing/plan
  - marketing/positioning
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

Create a Coga community channel for discussion, questions, and contributions from
interested users. Open decision (2026-07-14, reassigned zach → nick): Discord vs
a public Slack — pick one before the launch post ships, since the post needs a
"where to go" link.

Set up basic channels (#help, #contributing, #general) and link it prominently from the README.

Post a monthly changelog there as the regular public update. (#announcements) (I suppose this could also be part of relay-recurring)

Rollout (added 2026-06-12): add the Discord invite to the README, make the
relay repo public, and tell our users/friends about it. Repo-public is the
prerequisite for the other two.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
