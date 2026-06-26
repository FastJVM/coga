---
slug: dream-debug-cleanup-orphan-markers
title: Dream debug cleanup-orphan-markers
status: done
autonomy: auto
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dream/cleanup-orphan-markers
  steps:
  - name: run
    skills:
    - bootstrap/dream/tasks/cleanup-orphan-markers
    assignee: agent
secrets: null
---

## Description



## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-06-18T22:13:07+00:00
Task: `dream-debug-cleanup-orphan-markers`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.
