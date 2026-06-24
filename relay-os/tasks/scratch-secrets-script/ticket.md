---
slug: scratch-secrets-script
title: scratch secrets script
status: done
autonomy: auto
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: test/secret-probe
  steps:
  - name: probe
    skills:
    - test/secret-probe
    assignee: agent
secrets: null
---

## Description



## Context

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
