---
title: Slack webhook is env-only despite TOML comment implying it is configurable
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/sync
- relay/codebase
- dev/code
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
step: 4 (review)
---

## Description

Priority: medium. Config trap — contributes to the "Slack not firing"
confusion alongside the silent-response bug.

The Slack webhook is read **only** from the environment:
`os.environ.get("SLACK_WEBHOOK_URL")` (`src/relay/config.py:162`). There is no
`[slack].webhook` TOML key actually consumed. But the example `relay.toml` shows
a commented-out `webhook = "..."` (`example/relay-os/relay.toml:28-30`) — so a
user who follows that comment and sets the webhook in TOML gets **silence**: the
value is ignored and `slack_webhook` stays unset. Combined with `slack_enabled`
defaulting to True (`src/relay/config.py:422-432`), the failure is easy to hit and hard to
diagnose.

Make the TOML path real and make it the single documented way to configure the
webhook:

```toml
[slack]
webhook = "env:SLACK_WEBHOOK_URL"
```

Relay should consume `[slack].webhook` from TOML, resolve `env:` indirection the
same way other secrets do, and treat the webhook as a real secret. The bare
process environment must not remain a second independent configuration source:
`SLACK_WEBHOOK_URL` is only used when referenced by `webhook = "env:SLACK_WEBHOOK_URL"`.

Local config should override shared config for the webhook, matching
`[slack].enabled`: `relay.local.toml` may carry a machine-specific
`[slack].webhook`, while shared `relay.toml` can carry a safe `env:` reference
or omit the key. If both shared and local provide a webhook, local wins. Literal
non-empty webhook strings may be accepted by the parser, but examples and docs
must steer users to `env:` indirection and must never commit a real webhook URL.

Acceptance:

- `[slack].webhook = "env:SLACK_WEBHOOK_URL"` works in TOML.
- A bare exported `SLACK_WEBHOOK_URL` without `[slack].webhook` no longer counts
  as configured.
- There is exactly one documented way to set the webhook.
- The example config does not imply a path that silently no-ops.
- Enabled-but-unconfigured Slack is surfaced by `relay validate --check-slack`
  and by the first post path.
- Tests that currently assert TOML webhook is ignored are updated to assert the
  new contract.

## Context

Code: `src/relay/config.py` (`:162` webhook read, `:422-432` enabled default,
`_resolve_secrets` `:478-492`), `src/relay/slack.py` (missing-webhook and post
failure messages), `src/relay/validate.py` (`_slack_issues`, `probe_slack`),
`tests/test_slack.py`, and `tests/test_validate.py`.

Config/docs touchpoints: `example/relay-os/relay.toml:28-30` is the misleading
fixture comment; `src/relay/resources/templates/relay-os/relay.toml:31-45`
currently documents the old env-only path and should be updated to the new
TOML-backed secret path. Because this changes the webhook contract, update the
durable sync explanation in `relay-os/contexts/relay/sync/SKILL.md` and the
packaged template copy if one exists.

Pairs with `slack-post-ignores-http-response-so-bad-webhook-fa`; that sibling
handles bad webhook HTTP responses after a URL resolves. This ticket handles
where the URL comes from and how missing/unconfigured Slack is surfaced.
