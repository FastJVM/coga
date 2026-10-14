---
title: Make coga run on native Windows
status: draft
owner: nicktoper
workflow: null
---

## Description

README.md (source of truth) says Coga runs on Linux, Windows or macOS, but src/coga/git.py and src/coga/repl_supervisor.py import fcntl at module top, so every command, even coga --help, fails on native Windows. docs/contexts/coga/install/SKILL.md documents Windows as unsupported (WSL untested). Owner decision 2026-10-13: the README wins; port Coga to native Windows, then update coga/install to match.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
