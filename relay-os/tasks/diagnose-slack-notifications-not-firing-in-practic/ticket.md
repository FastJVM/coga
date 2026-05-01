---
title: Diagnose Slack notifications not firing in practice
status: active
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

Nick reports Slack notifications aren't actually firing in his setup,
even though `[slack] webhook = ...` is configured. The code path looks
correct on paper but messages aren't landing in Slack. We need to find
out why before any of the other Slack tickets matter.

Likely suspects (investigate, don't assume):

- Webhook URL malformed or expired (Slack rotates these).
- Webhook configured in the wrong file (`relay.toml` vs.
  `relay.local.toml`) and not getting loaded.
- `post_feed` failing silently — `src/relay/slack.py` swallows errors to
  stderr, which gets lost in scripted runs.
- Network egress blocked from the local environment.
- Channel the webhook posts to was archived or renamed.

Approach: instrument `slack.py` to log every attempted POST and its
response (status code, body) to a temp file or the task log, then run a
real command (`relay launch ...` on a draft ticket) and inspect. Once
the failure mode is known, fix it directly or split into a follow-up
ticket if it's bigger than a config issue.

## Context

- Audit reference: `docs/spec-audit.md` (Slack-related items, esp. error
  visibility concerns).
- Implementation: `src/relay/slack.py` (`post_feed`, `post_mention`).
- Config: `relay-os/relay.toml` (shared) and `relay-os/relay.local.toml`
  (per-machine; webhook lives in one of these).
- Related work in flight: `finish-slack-integration-features` ticket
  covers the broader Slack roadmap (channel routing, threading, retry).
  This ticket is narrower: just figure out why the existing single-
  webhook path is dead, fix it, and unblock the others.

## Acceptance criteria

- [ ] Root cause identified and written into this ticket's blackboard.
- [ ] Fix landed (config doc, code fix, or new validation — depends on
      the cause).
- [ ] After the fix, a `relay feed "test"` (or equivalent) reliably
      posts to Slack from Nick's setup.
- [ ] If the cause is "errors swallowed silently," loop back into
      `finish-slack-integration-features` for the structured-failure-path
      work — don't try to land that here.
