---
slug: coga-notifications/support-second-webhook
title: support-second-webhook
status: in_progress
owner: zach
human: zach
agent: claude
assignee: codex
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
step: 2 (peer-review)
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

## Dev

branch: important-webhook
worktree: ../coga-important-webhook

## Decisions

Key name — `important_webhook`, under `[notification.slack]` next to `webhook`. The
ticket Context already settled this; the `[notification.slack.webhooks]` map stays
unbuilt until a third channel exists.

Env var — `COGA_IMPORTANT_WEBHOOK_URL`. The blackboard previously said
`COGA_NOTIFICATIONS_WEBHOOK_URL`; the channel was renamed to coga-important on
2026-07-15, so the var follows the channel.

Unset `important_webhook` falls back to `webhook` with a stderr note, rather than
failing. An alert in the wrong channel beats a dead maintenance-fee sweep. Zach
approved 2026-07-15. This ticket owns the rule because it owns how the second
webhook resolves; `add-coga-slack-important` only asks for it.

No legacy `[slack]` or bare-env fallback for the new key — those paths exist for
backward compatibility and a new key has nothing to be compatible with. This forces
the legacy allowed-key set to split from the `[notification.slack]` one, or
`[slack].important_webhook` would be accepted and then silently ignored.

## What changed

Commit `18f50553` on `important-webhook`. Config only — no CLI surface yet.

- `config.py` — `_resolve_notification_slack_important_webhook`, `env:` indirection,
  local overrides shared, no legacy/bare-env fallback. New `cfg.slack_important_webhook`
  defaults to None so existing `Config(...)` call sites (`test_git.py`,
  `managed_skills.py`) keep working unchanged.
- `_ALLOWED_LEGACY_SLACK_KEYS` split from `_ALLOWED_SLACK_KEYS`, so
  `[slack].important_webhook` raises instead of being accepted and ignored.
- `slack.py` — `SlackChannel.webhook_for(important=)` picks the URL and owns the
  fallback; `send(important=False)` and `notification.post(important=False)` thread it.
- `coga/coga.toml` — key added as `env:COGA_IMPORTANT_WEBHOOK_URL`. Packaged template
  gets a commented example under "Optional Slack extras" (fresh repos stay opt-in).
- `contexts/coga/sync/SKILL.md` + its packaged twin — documented; the two were
  byte-identical and still are. Its "single source for the webhook URL" line was
  stale once a second webhook existed, so it now says "default".

Tests: 8 new in `tests/test_notification.py` (resolution, both routing directions,
fallback + stderr, local override, non-string, legacy rejection). Full suite 1215
passed / 1 skipped.

## Notes

Verified by driving the real `coga/coga.toml` through `load_config` +
`webhook_for`, not just the tests. That is what caught the first draft of the
fallback stderr message: it said "set the key in coga.toml" when the key was
already there and only the env var was missing, which would have sent a reader
to the wrong place. Message now names both causes.

Downstream repos carry their own `coga.toml`, so the patents repo needs its own
`important_webhook` before the maintenance-fee sweep's `--important` call routes
anywhere. The fallback above is what keeps that misconfiguration visible instead
of fatal.

For `add-coga-slack-important`: `post(..., important=True)` is the entry point;
the flag and the alert message shape are all that's left. That ticket's body still
says "Coga Notifications" for the channel renamed to coga-important on 2026-07-15
— worth a pass when it starts.
