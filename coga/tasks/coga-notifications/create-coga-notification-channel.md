---
slug: coga-notifications/create-coga-notification-channel
title: create-coga-notification-channel
status: draft
autonomy: interactive
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

This ticket is the build plan to create the actual Coga Notifications channel:
the webhook, the routing that sends only action-needed notifications here, and
@-ing the responsible user.

The patent sweeps are its first consumer, but the channel itself is a general
coga capability.

---
## Building Coga Notifications

 Ensure coga can handle a second, named web hook (two live at once) — it's only built for 1 at the moment
 Create the `coga-notifications` channel in Slack and add an incoming web hook to it
 Build `coga slack --important` that points notifications to the channel
 Each domain script (patents first) decides when to post a human-action alert through it
 The notification will include the ticket slug
 @ the user set in the coga.toml property field in every notification; no notification ever goes out un-tagged
 The mention renders as a real Slack ping, not plain text

---

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
