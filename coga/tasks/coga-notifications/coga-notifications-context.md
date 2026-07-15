---
slug: coga-notifications/coga-notifications-context
title: coga-notifications-context
status: draft
mode: agent
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

This ticket is the unit of work to build a context block that describes how we
plan to handle important notifications and who's responsible for acting on them.
It's also meant to explain how it differs from coga-flow.

The deliverable is the context block itself — the routing convention any script
can follow to raise a human-action notification. Building the channel and its
webhook, and the coga.toml recipient field, are separate tickets.

## Coga Notifications

1. "Coga Notifications" will be our new Slack channel strictly for notifications
   that need human action.

2. Coga's automatic state-transition broadcasts (create / bump / mark) stay in
   coga-flow.

3. We don't want to be inundated with notifications, but we don't want anything
   to fall through the cracks.

4. Notifications land here automatically — any script that detects an
   action-needed event runs `coga slack --important` to post it to Coga
   Notifications (e.g. a patent sweep posting "maintenance fee due").

5. By default every `--important` notification @'s the user set in the coga.toml
   property field — the triage owner it all lands on.

6. That user either handles it, or hands it off by running `coga slack --important`
   again, @'ing whoever should own it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
