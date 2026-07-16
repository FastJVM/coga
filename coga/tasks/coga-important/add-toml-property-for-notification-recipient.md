---
slug: coga-important/add-toml-property-for-notification-recipient
title: add-toml-property-for-notification-recipient
status: in_progress
owner: zach
human: zach
agent: claude
assignee: codex
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
step: 2 (peer-review)
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

## Dev

- branch: important-recipient
- worktree: ../coga-important-recipient
- commit: fa892703 (rebased onto origin/main 82631ba2 — picked up doc-refresh
  PRs #565–#574; only #569 touched a file I edited, sync SKILL.md, and replayed
  clean)
- tests: full suite green (1236 passed pre-rebase; config+notification 131
  passed post-rebase)

## Implementation (2026-07-16, from main after #553 merged)

Followed the "Ready to implement" shape below. Landed in `src/coga/config.py`:
`"important_recipient"` added to `_ALLOWED_SLACK_KEYS` only (not the legacy set);
new `_resolve_notification_slack_important_recipient` mirroring the webhook
resolver but with no `_resolve_secret_value`, no legacy/env fallback, empty
string collapsing to None; `slack_important_recipient` field on `Config`, plumbed
through `_parse_slack_notification`'s return tuple (placed right after
`important_webhook`) and `load_config`. Docs in both `coga.toml` copies and both
`coga/sync` SKILL.md copies. Config-resolution tests in
`tests/test_notification.py`, mirroring the `important_webhook` cases. Value is
not spent in `slack.py` — `coga-important/add-coga-slack-important` is the consumer.

## Blocked: this ticket's base does not exist on main

Every anchor the ticket's Context names lives only on PR #553's unmerged
`important-webhook` branch, not on `main`:

- `_resolve_notification_slack_important_webhook` — added by #553.
- `_ALLOWED_LEGACY_SLACK_KEYS` — added by #553. On main, `config.py:454` still
  checks the legacy `[slack]` table against `_ALLOWED_SLACK_KEYS`. The ticket
  says "keep it out of `_ALLOWED_LEGACY_SLACK_KEYS`", which cannot be done to a
  set that does not exist.
- `coga slack --important` — added by #553. Main has no such flag, so the
  property would name the recipient of a post that cannot be made.

PR #553 (`support-second-webhook`) is OPEN, opened 2026-07-15 22:20Z, unreviewed.

## Why I did not just pick a base

Facts that make this a real choice rather than a detail:

- The repo squash-merges (every merged PR's `mergeCommit.oid` != `headRefOid`;
  main is linear with `(#NNN)` subjects). A branch stacked on
  `important-webhook` keeps #553's two commits by hash after #553 squashes into
  main, so the later rebase must drop them by hand.
- 40 of 40 PRs in this repo target `main`. No stacked-PR precedent.
- `coga/skills/code/open-pr/recipe.py:143` sets `base = cfg.git_control_branch`
  and passes it at line 269 as `gh pr create --base`. There is no per-ticket
  base override, so a stacked branch opens a PR against `main` that displays
  #553's diff plus mine until #553 merges.
- open-pr also fails loud on material source drift from the control branch,
  which is what a squashed #553 would look like to my stacked branch.

The hunks this ticket must touch — `_ALLOWED_SLACK_KEYS`, the
`_parse_slack_notification` signature and return tuple, the `Config` field list,
`load_config`'s unpack, `coga.toml`, and the `coga/sync` SKILL.md — are the same
hunks #553 rewrites. Any base other than #553's lands a conflict on each one.

## Options put to the owner

1. Wait for #553 to merge, then implement from main. Clean, small diff; costs a
   round-trip.
2. Stack on `important-webhook` now. Fat PR until #553 merges, then a
   `rebase --onto` through the squash.
3. Branch from main and add `_ALLOWED_LEGACY_SLACK_KEYS` here. Contradicts the
   ticket and duplicates #553.

## Decision — option 1 (zach, 2026-07-15)

Wait for #553 to merge, then implement from main. No branch, no worktree, no
code written.

## Ready to implement once #553 is on main

The shape, for whoever picks this up:

- Add `"important_recipient"` to `_ALLOWED_SLACK_KEYS` in `src/coga/config.py`,
  alongside `"important_webhook"` in the `_ALLOWED_LEGACY_SLACK_KEYS | {...}`
  union. Do not add it to `_ALLOWED_LEGACY_SLACK_KEYS` — `[slack].important_recipient`
  must be rejected, not silently ignored.
- Add `_resolve_notification_slack_important_recipient`, mirroring
  `_resolve_notification_slack_important_webhook` (local overrides shared, no
  legacy `[slack]` fallback, no env fallback, `ConfigError` on a non-string).
  Drop the `_resolve_secret_value` call — a coga name is not a secret.
- Plumb `slack_important_recipient: str | None = None` through the `Config`
  dataclass, `_parse_slack_notification`'s return tuple, and `load_config`.
- Unset resolves to None; `render_text`'s owner mention stands. This ticket does
  not spend the value — `coga-important/add-coga-slack-important` is the consumer.
- Document the key in `coga/coga.toml` and
  `src/coga/resources/templates/coga/coga.toml`, and in the `coga/sync` context
  (both the live copy and `src/coga/resources/templates/coga/bootstrap/`).
- Tests belong in `tests/test_notification.py`, following the
  `important_webhook` cases #553 adds there.

---

## Blockers

- [x] [2026-07-15 17:55] [agent:claude] id=20260715T175503 Depends on unmerged PR #553 (support-second-webhook). The ticket's three named anchors — _resolve_notification_slack_important_webhook, _ALLOWED_LEGACY_SLACK_KEYS, and the coga slack --important flag — exist only on that branch, not on main. Owner chose (2026-07-15) to wait for #553 to merge rather than stack or duplicate the split. Unblock with 'coga unblock add-toml-property-for-notification-recipient --answer "#553 merged"' once it lands; the blackboard records the ready-to-implement shape.
  resolved: [2026-07-16 11:35] [human:zach] #553 merged (mergeCommit 5c44827d, 2026-07-16 17:00Z); anchors _ALLOWED_LEGACY_SLACK_KEYS, _ALLOWED_SLACK_KEYS, _resolve_notification_slack_important_webhook and coga slack --important all present on origin/main. Proceeding with option 1: implement from main.

## Blocker reminders

- 345ef866cdda last_reminded: 2026-07-15 20:14
