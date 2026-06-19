---
title: relay-forces-https
status: in_progress
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

SSH-auth users are forced through HTTPS — Relay hardcodes the HTTPS upstream URL and HTTPS-leaning skill imports, so they need a token despite working SSH keys.
Make the git transport respect the user's setup: allow SSH URLs or auto-detect.
Touchpoints: RELAY_REPO_URL/clone_upstream in commands/update.py, source normalization in skill_manager.py

## Context

