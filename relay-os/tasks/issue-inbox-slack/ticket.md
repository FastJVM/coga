---
title: issue-inbox-slack
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Enrich Relay's existing Slack posts into an inbox: panics carry the blocker reason and required action, dones carry the outcome — readable without opening a terminal.
Every post links the next step: the relay command to run or a link to the ticket file.
Webhook-only; no Slack app, no buttons, no server.

## Context

