---
slug: coga-important/context
title: context
status: in_progress
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

This ticket is the unit of work to build a context block that describes how we
plan to handle important notifications and who's responsible for acting on them.
It's also meant to explain how it differs from coga-flow.

The deliverable is the context block itself — the routing convention any script
can follow to raise a human-action notification. The channel already exists; its
webhook and the coga.toml recipient field are separate tickets.

## coga-important

1. `coga-important` is our Slack channel strictly for notifications that need
   human action.

2. Coga's automatic state-transition broadcasts (create / bump / mark) stay in
   coga-flow.

3. We don't want to be inundated with notifications, but we don't want anything
   to fall through the cracks.

4. Notifications land here automatically — any script that detects an
   action-needed event runs `coga slack --important` to post it to
   `coga-important` (e.g. a patent sweep posting "maintenance fee due").

5. By default every `--important` notification @'s the user set in the coga.toml
   property field — the triage owner it all lands on.

6. That user either handles it, @'s someone in the Slack thread, or opens a ticket
   if it's real work.

7. Handing off stays a plain Slack @ and gets no Coga machinery — a thread reply
   keeps the alert's context, while a second `coga slack` post would land
   disconnected from it and add the channel noise point 3 rules out.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
