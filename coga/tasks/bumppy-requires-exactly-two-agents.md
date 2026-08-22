---
slug: bumppy-requires-exactly-two-agents
title: bumppy-requires-exactly-two-agents
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

From Zach's local-llm testing: "bump.py:44 requires exactly two for assignee: other-agent. Nothing in coga/workflows/ uses that token today, so you're fine but a future workflow using it will fail with all three declared."

I believe we need to allow bump.py to accept another agent so workflows don't fail. 

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
