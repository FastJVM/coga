---
title: webhook for slack is public
status: draft
owner: nicktoper
workflow: maintenance/with-approval
---

## Description

Rotate the coga Slack state-transition webhook, because its full URL is
public. Before the redaction fix in PR #629 (2026-07-22), failed Slack posts
logged the raw `requests` ConnectionError, and that text contains the URL path
(`/services/T0AG1AVQYR1/B0B0KD0BTQB/<secret>`). Twenty-four such lines,
written 2026-06-23 to 2026-07-11, sit in `coga/log.md` on `origin/main` of the
**public** `FastJVM/coga` repo and in its git history. Anyone can post into
the channel until the URL is revoked.

Done means all of the following:

- The old webhook is revoked in Slack, and a probe of it is classified
  `revoked` (HTTP 404 / `no_service`).
- A new webhook is live, and every place that exported the old URL now
  exports the new one.
- `coga validate --check-slack` passes from both the coga and thinkpick
  checkouts.
- The new URL never appears in any tracked file, ticket, blackboard, or
  log.

## Context

- **Which webhook leaked:** `SLACK_WEBHOOK_URL`, the state-transition
  channel. As of authoring it is exported from `~/.bashrc` and still equals
  the leaked value. `COGA_IMPORTANT_WEBHOOK_URL` (`important_webhook`, the
  coga-important channel) does not appear in the log and is out of scope
  unless the inventory finds it exposed.
- **Who reads it:** `coga/coga.toml` (`webhook = "env:SLACK_WEBHOOK_URL"`) and
  `thinkpick/coga/coga.toml` (same variable; public repo, but it holds no
  copy of the URL). The tablet repo has Slack commented out. The inventory
  step should also check for other machines, CI or GitHub Actions secrets,
  `coga.local.toml` overrides, and 1Password items that hold the URL.
- **The code is already fixed:** `slack_response.format_slack_request_error`
  logs only a fixed category (e.g. `ConnectionError: DNS/name-resolution
  failure`), and `slack_response.redact_slack_webhook_credentials` covers
  response bodies. Do not change code for this ticket.
- **Explicitly out of scope:** redacting the old lines in `coga/log.md`
  (the log is append-only, and once rotated the old URL is dead) and
  rewriting git history.
- **Owner-only actions:** creating the new webhook and revoking the old one
  in Slack, and editing `~/.bashrc` or other secret stores. The agent must
  not ask for the new URL to be pasted into chat or into the ticket. It
  verifies by probing through `coga validate --check-slack` and by checking
  only whether the env var still matches the old URL's `B0B0KD0BTQB` id,
  without printing the value.
- **Probing the old URL:** `slack_response.classify_slack_response` maps 404
  or `no_service` to `revoked`. Redact the URL in any command output that is
  recorded on the blackboard.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
