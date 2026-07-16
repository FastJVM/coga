---
slug: coga-important/add-toml-property-for-notification-recipient
title: add-toml-property-for-notification-recipient
status: in_progress
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- coga/sync
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

Add `[notification.slack].important_recipient` to coga.toml, naming the coga user
@'d on every `coga slack --important` post. Alerts need one triage owner they all
land on, and `--important` today @'s the ticket owner — whoever filed the ticket,
not whoever should act. This ticket adds the property and its resolution only;
`coga-important/add-coga-slack-important` is the consumer that spends it.

## Context

- The key sits under `[notification.slack]` next to `webhook` and `important_webhook`.
- `_resolve_notification_slack_important_webhook` in `src/coga/config.py` is the nearest pattern to follow.
- The value is a coga name, not a Slack member ID.
- `mention` in `src/coga/notification/slack.py` already resolves a name through `[notification.slack.users]`.
- The name is not a secret, so it takes no `env:` indirection.
- `render_text` in `src/coga/notification/slack.py` builds the `[project] [@owner]` prefix the recipient replaces.
- Unset resolves to None and the owner mention stands, matching the `important_webhook` fallback rule.
- The key must join `_ALLOWED_SLACK_KEYS` in `src/coga/config.py`, or config load fails loud on it.
- Keep it out of `_ALLOWED_LEGACY_SLACK_KEYS` so `[slack].important_recipient` is rejected rather than silently ignored; that split lands with PR #553.
- `coga-important/context` point 5 is the source for recipient-on-`--important`-only.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
