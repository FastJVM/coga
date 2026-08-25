---
slug: parse-agents-rejects-cogalocaltoml
title: parse-agents-rejects-cogalocaltoml
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

From Zach's testing with local-llm: _parse_agents hard-rejects [agents.*] there (in coga.local.toml)

coga.local.toml shouldn't override the agent additions (so they don't need to be committed.)

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
