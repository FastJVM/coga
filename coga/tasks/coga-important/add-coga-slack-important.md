---
slug: coga-important/add-coga-slack-important
title: add-coga-slack-important
status: draft
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Add `--important` to `coga slack` so any script can post a human-action
notification to `coga-important`. It posts through the second webhook and @'s
the recipient set in coga.toml instead of the ticket owner.

## Context

- `coga slack` is `src/coga/commands/slack.py`; it calls `post` in `src/coga/notification/__init__.py`.
- `render_text` in `src/coga/notification/slack.py` builds the `[project] [@owner]` prefix.
- `--important` replaces the owner mention with the recipient; every post is tagged.
- The mention already renders as a real ping through `[notification.slack.users]`.
- The message carries the ticket slug, as `coga slack` already does.
- Depends on `coga-important/support-second-webhook` and `coga-important/add-toml-property-for-notification-recipient`.
- First consumer is the patents repo `repo/utility/maintenance-fee-sweep`.

<!-- coga:blackboard -->

## Already landed

The `--important` flag and its routing to `important_webhook` landed in PR #553
(`coga-important/support-second-webhook`), added during that ticket's peer-review
step because #553's docs described a flag the command did not expose. Don't
re-implement it. `SlackChannel.webhook_for(important=)` picks the webhook and
`post(..., important=True)` threads the flag through.

What this ticket still owns:

- The alert message shape. `--important` calls `render_text` before the webhook is
  picked, so it still renders the FYI shape the Production notes below call wrong.
- The recipient mention. `--important` still @'s the ticket owner. The coga.toml
  recipient key belongs to `coga-important/add-toml-property-for-notification-recipient`,
  a bare draft with no workflow, so this half is blocked until that lands.

## Production notes

Message shape — from the 2026-07-15 rehearsal, which posted through the existing
`coga slack` path into the live channel:

```
coga APP  [coga] [@zach] 💬 claude on coga-notifications/create-coga-notification-channel
          "create-coga-notification-channel": dress rehearsal
```

That is the FYI shape and it is wrong for an alert. Nobody is "on" a maintenance-fee
alert, the `[coga]` prefix repeats the app name, and the title repeats the slug.
`--important` needs its own shape, closer to:

```
[@zach] ⚠️ patent-fake-widget #9999999 — Window 2 fee not recorded, closes 2027-01-15
```

Testable offline — `tests/test_notification.py` fakes the webhook with
`monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)` and asserts
on the captured payload. Cover: `--important` posts to the second webhook, a bare
post still goes to `webhook`, and the recipient mention renders as `<@UID>`.
