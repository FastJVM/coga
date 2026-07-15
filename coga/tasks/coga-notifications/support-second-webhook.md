---
slug: coga-notifications/support-second-webhook
title: support-second-webhook
status: active
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Coga resolves one Slack webhook today, so every post lands in the same channel.
Add a second webhook so Coga Notifications posts to its own channel while
state-transition broadcasts stay in coga-flow.

## Context

- Webhook resolution is `_resolve_notification_slack_webhook` in `src/coga/config.py`.
- `SlackChannel.send` reads the resolved URL from `cfg.slack_webhook` in `src/coga/notification/slack.py`.
- The new key sits under `[notification.slack]` next to `webhook`.
- Use `env:` indirection so the URL stays out of the committed file.
- `coga-notifications/add-coga-slack-important` is the consumer.

<!-- coga:blackboard -->

## Production notes

Open decision — the key name and shape. Two options:

- `important_webhook = "env:COGA_NOTIFICATIONS_WEBHOOK_URL"` — one more key, mirrors
  the existing `webhook`, no new concept.
- `[notification.slack.webhooks]` name → URL map — general, but nothing needs a third
  webhook yet.

Leaning `important_webhook` until a third channel exists.
