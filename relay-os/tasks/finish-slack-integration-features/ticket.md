---
title: Finish Slack integration features
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
workflow: code/with-review
---

## Description

Slack is plumbed but minimal. The recent simplification (commit `9b4b7c2`)
collapsed the integration to a single `post(cfg, message)` posting plain
text to one shared channel. That shape is the one we want to keep — this
ticket does **not** re-introduce threading, per-team channel routing, bot
tokens, or on-call paging. Instead, finish the simple version: make it
reliable, surface failures, and let other apps share the same webhook.

## Current state

- `src/relay/slack.py` exposes `post(cfg, message)`. No threading, no
  per-call channel selection, no mentions.
- Single webhook configured via `[slack] webhook = "..."` in `relay.toml`.
- When no webhook is set, the message is written to `stderr` prefixed with
  `[slack]`. When a `requests.post` fails, the error is also written to
  stderr and swallowed.
- Callers: `bump.py`, `launch.py`, `launch_script.py`, `feed.py`,
  `panic.py`. Each calls `post()` with a fully-formed message string.

## In scope

1. **Validation.** `relay validate` should fail loudly if `slack.webhook`
   is set but unreachable (e.g. a HEAD or a dry POST that the user can
   opt out of). Catch typos and revoked URLs at config time, not at
   first `bump`.
2. **Shared-webhook env-var fallback.** Add an env-var fallback (e.g.
   `$RELAY_SLACK_WEBHOOK` or a shared `$SLACK_WEBHOOK_URL` — pick a name
   in implementation) so multiple apps on the same machine can post
   through one Slack app config without each duplicating the URL in their
   own config file. Resolution order: `relay.toml` value first, then env
   var, then stderr fallback. Document the convention in
   `relay.toml`-template comments and the README slack section.
3. **Structured failure path.** Today a network failure during `bump`
   silently disappears into stderr. Surface failures somewhere durable —
   simplest option: write to a dotfile (`relay-os/.slack-failures.log`)
   with timestamp + message + error, and have `relay status` (or a new
   one-liner) note when failures are present. Goal: scripted runs can
   tell whether posts landed.
4. **Optional retry.** A small in-process retry (≤3 attempts, exponential
   backoff capped at a few seconds) on transient `RequestException`. No
   on-disk queue — we're not building durable delivery here. If retries
   exhaust, fall through to (3).

## Out of scope

- Threading per task (deliberately removed in `9b4b7c2`).
- Per-team or per-context channel routing.
- Bot-token migration / `chat.postMessage`.
- `relay panic` paging an on-call rotation — keep the existing
  channel-style mention.
- Multiple workspaces.
- A relay-hosted webhook proxy / daemon (separate ticket if pursued).
- Inbound Slack → relay events (separate ticket).

## Context

- Implementation: `src/relay/slack.py`. Callers under
  `src/relay/commands/`. Config schema: `src/relay/config.py` (look for
  `slack_webhook`).
- Templates: `src/relay/resources/templates/relay-os/relay.toml` —
  update the commented `[slack]` block to document the env-var fallback.
- `relay validate` lives at `python -m relay.validate`; extend it rather
  than adding a parallel command.
- Don't bring back `post_feed` / `post_mention`. The simplification was
  intentional.

## Acceptance criteria

- [ ] `relay validate` reports a clear failure when `slack.webhook` is
      set but the URL is unreachable / 4xx-on-empty-post.
- [ ] Setting `$RELAY_SLACK_WEBHOOK` (or whichever name lands) with no
      `[slack]` block in `relay.toml` posts successfully.
- [ ] A simulated network failure during `relay bump` writes a record to
      the structured failure path and is visible from `relay status` (or
      equivalent surface).
- [ ] Tests cover: missing config → stderr; env-var only → posts; toml
      override of env var; retry then success; retry exhaustion →
      structured failure log.
- [ ] README + `relay.toml` template comment document the env-var
      convention.
