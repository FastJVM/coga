---
title: Test and fix install on macOS and Windows
status: active
owner: zach
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
contexts:
- coga/install
- coga/testing/clean-install
agent: claude
---

## Description

Zach (marketing) has a Mac and a Windows machine. Walk a clean install of coga on each, the way a new user would (uv tool install coga, then coga init, coga build, a first ticket), and fix what breaks with the agent in the same session. macOS works but has known first-run problems: the Xcode Command Line Tools git stub, and the system Python 3.9 being below the 3.11 floor. Native Windows does not start at all: src/coga/git.py imports fcntl at module top, so even coga --help fails, and repl_supervisor.py and megalaunch.py also need pty/termios/tty. The deep Windows port is tracked in make-coga-run-on-native-windows (owner decision 2026-10-13: README claims Windows support, so port it). This ticket is the hands-on test-and-fix pass that feeds it. Deliverables: a findings list per OS on the blackboard, fixes as PRs, and docs/contexts/coga/install/SKILL.md updated to match what actually works.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
