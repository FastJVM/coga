---
title: Validate Slack user IDs at config load
status: draft
mode: interactive
owner: nick
assignee: claude1
contexts:
  - relay/architecture
  - relay/principles
  - relay/codebase
  - relay/current-direction
  - relay/project-stage
workflow:
  name: code/with-review
  steps:
    - name: implement
      skill: code/implement-and-pr
    - name: review
step: 1 (implement)
---

## Description

`src/relay/slack.py` (around lines 35-40) falls back to plain text
`@<name>` when a user has no Slack ID configured. Slack does not render
that as a real mention — it's just the literal string `@nick`, no
notification, no highlight. The fallback hides the misconfiguration.

Fix: at `Config` load, validate that every user who can be mentioned has
a `slack_id` set. If any user is missing one, fail loudly with a
message naming the user and the config file to fix. No silent string
fallback.

This pairs with the broader Slack work but is small and standalone:
config-load validation only, no networking, no API calls.

## Context

- Audit entry: `docs/spec-audit.md` §D.22.
- Implementation: `src/relay/slack.py` (`post_mention` fallback path).
- Config load: `src/relay/config.py` (or wherever `Config` is parsed) —
  add the validation here so `relay validate` catches it too.
- User config: `relay-os/relay.toml` (and `relay.local.toml` for local
  overrides; `slack_id` is per-user).

## Acceptance criteria

- [ ] Config load raises if any user can be mentioned but has no
      `slack_id`.
- [ ] Error names the user and the config file to fix.
- [ ] `relay validate` surfaces the same error (likely free if validation
      runs through Config load).
- [ ] No `@<name>` plaintext fallback remains in `slack.py`.
- [ ] Test covers: user with id (passes), user without id but never
      mentioned (passes), user without id who is mentioned (fails).
