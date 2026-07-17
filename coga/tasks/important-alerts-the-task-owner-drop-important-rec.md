---
slug: important-alerts-the-task-owner-drop-important-rec
title: important alerts @ the task owner; drop important_recipient
status: in_progress
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

Remove the `[notification.slack].important_recipient` config key. Important
Slack alerts @ the task owner, which is already how `render_text` behaves, so
no renderer change is needed. Update the `coga/sync` and `coga/important`
contexts to describe owner-based triage instead of a configured recipient.

## Context

`important_recipient` shipped in #575 but nothing in the renderer reads it —
`render_text` already @'s the ticket owner via `mention(cfg, owner)`. PR 578
would have wired the key in and added a `⚠️` alert prefix; both are dropped, so
close PR 578 as part of this.

Removing the key means the whole plumbing surface, not just template lines: the
`Config.slack_important_recipient` field, the
`_resolve_notification_slack_important_recipient` resolver, the
`important_recipient` entry in `_ALLOWED_SLACK_KEYS`, the example comment at
`config.py:401-406`, and the `important_recipient` tests in
`tests/test_notification.py`. Drop `important_recipient` only —
`important_webhook` is a separate, live key (`webhook_for` reads it) and must
stay; the two sit adjacent everywhere, so edit surgically.

In both `coga/coga.toml` and the packaged template the key is only a commented
example: deleting those lines prevents no crash, so remove them for accuracy,
not safety. The real fail-loud risk is the reverse — once the allow-list entry
is gone, an active `important_recipient = …` in a downstream `coga.toml` or a
`coga.local.toml` will fail config load.

Rewrite the `coga/sync` and `coga/important` contexts to describe owner-based
triage instead of a configured recipient. Keep each live `coga/contexts/` copy
and its packaged `src/coga/resources/templates/coga/bootstrap/contexts/` copy in
sync (four files: sync + important, live + packaged).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
