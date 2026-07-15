---
slug: coga-notifications/add-coga-slack-important
title: add-coga-slack-important
status: draft
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

Add `--important` to `coga slack` so any script can post a human-action
notification to Coga Notifications. It posts through the second webhook and @'s
the recipient set in coga.toml instead of the ticket owner.

## Context

- `coga slack` is `src/coga/commands/slack.py`; it calls `post` in `src/coga/notification/__init__.py`.
- `render_text` in `src/coga/notification/slack.py` builds the `[project] [@owner]` prefix.
- `--important` replaces the owner mention with the recipient; every post is tagged.
- The mention already renders as a real ping through `[notification.slack.users]`.
- The message carries the ticket slug, as `coga slack` already does.
- Depends on `coga-notifications/support-second-webhook` and `coga-notifications/add-toml-property-for-notification-recipient`.
- First consumer is the patents repo `repo/utility/maintenance-fee-sweep`.

<!-- coga:blackboard -->

## Production notes

Testable offline — `tests/test_notification.py` fakes the webhook with
`monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)` and asserts
on the captured payload. Cover: `--important` posts to the second webhook, a bare
post still goes to `webhook`, and the recipient mention renders as `<@UID>`.
