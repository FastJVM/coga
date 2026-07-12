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

1. Ensure coga can handle another web hook (it's only built for 1 at the moment)
2. Create a new web hook and connect it to the coga-notifications channel
3. Build routing logic to have the channel receive only notifications that require human attention
4. The notification will produce all of the identifying information to find the matter easily from the Slack channel
5. Includes the ticket title and the date/deadline
6. Includes a link to the ticket.
7. @ the user set in the coga.toml property field in every notification; no notification ever goes out un-tagged
8. The mention renders as a real Slack ping, not plain text

---

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
