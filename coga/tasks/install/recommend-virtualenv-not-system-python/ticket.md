---
slug: install/recommend-virtualenv-not-system-python
title: Onboarding install should use a virtualenv, not system Python
status: in_progress
mode: agent
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- dev/code
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
secrets: null
step: 1 (implement)
---

## Description

Following the README, a new user installs Relay's dependencies into their system
Python; many external users won't want their system Python polluted. Make the
recommended install path a virtualenv (create + activate + install), with a
global/system install as an explicit opt-out. While in the same README install
block, also fix the `python` vs `python3` nit — macOS ships only `python3`, so
the copy-pasted command fails out of the box.

## Context

Reported by Greg; he got it working in a venv himself, but only by deviating
from the docs. Touchpoint: README Getting Started / quickstart, currently under
editorial revision in `marketing/readme-and-docs`. Distinct from
`document-cross-machine-sandbox-dev-loop-friction-i` (that captures the
*contributor* dev-loop python-version friction — .venv 3.9 vs the 3.11+ Relay
needs); this one is about first-time *user* onboarding.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
