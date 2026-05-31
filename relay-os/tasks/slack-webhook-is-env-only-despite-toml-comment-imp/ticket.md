---
title: Slack webhook is env-only despite TOML comment implying it is configurable
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: medium. Config trap — contributes to the "Slack not firing"
confusion alongside the silent-response bug.

The Slack webhook is read **only** from the environment:
`os.environ.get("SLACK_WEBHOOK_URL")` (`config.py:156`). There is no
`[slack].webhook` TOML key actually consumed. But the example `relay.toml` shows
a commented-out `webhook = "..."` (example `relay.toml:29-30`) — so a user who
follows that comment and sets the webhook in TOML gets **silence**: the value is
ignored and `slack_webhook` stays unset. Combined with `slack_enabled`
defaulting to True (`config.py:421`), the failure is easy to hit and hard to
diagnose.

Pick one and make it consistent:
- (a) Actually consume `[slack].webhook` from TOML (with `env:` indirection like
  other secrets), and treat it as a real secret; or
- (b) Remove the misleading commented example and document clearly that the
  webhook is env-only, ideally with a `relay validate`/startup check that warns
  when `slack_enabled` is true but no webhook resolves.

Option (a) is more consistent with the rest of config (secrets support `env:`
indirection); the webhook being the one env-only secret is itself a smell.

Acceptance: there is exactly one documented way to set the webhook, and it
works; the example config does not imply a path that silently no-ops; enabled-
but-unconfigured Slack is surfaced (warn at validate or fail at first post).

## Context

Code: `src/relay/config.py` (`:156` webhook read, `:421` enabled default,
`_resolve_secrets` `:424`), `example/.../relay.toml:29-30` (misleading comment).
Pairs with `slack-post-ignores-http-response-so-bad-webhook-fa`.
