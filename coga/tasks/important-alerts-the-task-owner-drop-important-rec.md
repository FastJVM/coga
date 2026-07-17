---
slug: important-alerts-the-task-owner-drop-important-rec
title: important alerts @ the task owner; drop important_recipient
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

## Plan

Drop `[notification.slack].important_recipient` end to end. `important_webhook`
is a separate live key and stays. Verified nothing reads
`slack_important_recipient`: `render_text` (`notification/slack.py:39`) @'s the
owner passed by callers, and `coga slack --important` passes
`owner=ticket.owner or cfg.current_user` (`commands/slack.py:58`). So the
owner-mention is already the behavior; removing the key changes no runtime path.

Surface (surgical, recipient only):
- `src/coga/config.py`: drop the `slack_important_recipient` field, its unpack +
  constructor kwarg, the `"important_recipient"` allow-list entry, the resolver
  call + return-tuple slot + type-annotation line, and the whole
  `_resolve_notification_slack_important_recipient` fn. Update the comment above
  `_ALLOWED_SLACK_KEYS` to name only `important_webhook`.
- `tests/test_notification.py`: delete the `important_recipient` test section.
- `coga/coga.toml` + packaged `src/coga/resources/templates/coga/coga.toml`:
  remove the commented `important_recipient` example blocks.
- `coga/contexts/coga/{sync,important}/SKILL.md` + packaged copies: rewrite to
  owner-based triage, drop the recipient key/field.

## Notes

- PR 578 is already CLOSED (`gh pr view 578`) — nothing to close.
- Live and packaged `sync`/`important` contexts are byte-identical pre-edit; keep
  them identical after.
- The fail-loud win: once the allow-list entry is gone, an active
  `important_recipient = …` in a downstream `coga.toml`/`coga.local.toml` raises
  at load instead of being silently accepted.

## Dev

branch: drop-important-recipient
worktree: /Users/zach2179/dev/coga-drop-important-recipient

## Done (implement step)

Removed `important_recipient` end to end; `important_webhook` untouched.
- `config.py`: dropped the `slack_important_recipient` field, unpack + constructor
  kwarg, allow-list entry, resolver call + return slot + type-annotation line, and
  the `_resolve_notification_slack_important_recipient` fn. Comment above
  `_ALLOWED_SLACK_KEYS` now names only `important_webhook`.
- `tests/test_notification.py`: deleted the `important_recipient` section (6 tests
  + helper).
- Both `coga.toml` copies: removed the commented `important_recipient` examples.
- `coga/sync` + `coga/important` contexts (live + packaged): rewritten to
  owner-based triage; live/packaged copies verified byte-identical.

Verification (all run against the worktree source via `PYTHONPATH=…/src`, since
the editable install points at the primary checkout):
- Full suite: 1289 passed, 1 skipped.
- Field removed / webhook kept / resolver gone / allow-list correct — asserted.
- Fail-loud confirmed: an active `important_recipient = …` now raises
  `ConfigError: unknown key(s) ['important_recipient']` at load.
- `coga validate --json`: introduces zero issues vs `main` (the lone delta is a
  `missing-user` warning from the fresh worktree having no gitignored
  `coga.local.toml`).
- PR 578 already CLOSED — nothing to close.
