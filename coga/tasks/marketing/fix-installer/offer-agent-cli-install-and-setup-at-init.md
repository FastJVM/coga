---
title: Offer agent CLI install and setup at init
status: in_progress
owner: nicktoper
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
step: 1 (execute)
agent: claude
launch_generation: 8c713222-6190-49c2-bad0-e92b82e13a72
---

## Description

Follow-up to PR #942 (init offers to install missing git/gh/op). New users who have no agent CLI hit 'Agent CLI not found in PATH' on their first `coga build`/`coga launch`. Make interactive `coga init` offer to pick an agent (Claude Code or Codex), install it via its official installer or package manager, run its login, and set the default agent in coga.toml. Non-interactive init must not prompt. Open questions for the owner: which installers to trust (npm, curl script, brew cask), whether init may edit coga.toml agent defaults, and how this interacts with `coga build`'s onboarding. Update `coga/install`, `coga/init`, `coga/agents` and their packaged twins.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
