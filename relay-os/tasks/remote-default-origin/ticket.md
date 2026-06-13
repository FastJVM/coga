---
title: remote-default-origin
status: active
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

A user with a non-standard remote name (upstream instead of origin) found Relay assumes origin when pushing — it works for the default case but silently breaks for anyone with a different layout.
Make the remote name configurable (e.g. remote = "origin" in relay.toml, defaulting to origin) instead of hardcoded.
Sweep the one hardcoded push in skill_manager.py plus any skill prompts that say origin, and have them use the configured name.

## Context

