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
   is set but the webhook is dead. Slack incoming webhooks reject `GET`
   and `HEAD` (405) and reject empty payloads — exploit that as a
   liveness probe. Concrete approach: `POST {"text": ""}` with a 5s
   timeout. A live webhook returns HTTP 400 with body containing
   `no_text` (Slack rejected the empty text but the URL is alive); a
   revoked / unknown webhook returns 404 with `no_service`; any
   `requests.exceptions.RequestException` means unreachable. Report
   each case with a distinct message. The implementer should sanity-check
   actual response codes/bodies against a real Slack webhook before
   pinning the assertion strings — Slack's wire format is the source of
   truth, not this ticket. The empty-text payload is not expected to
   produce a visible Slack message; confirm during implementation.
   Catch typos and revoked URLs at config time, not at first `bump`.
2. **Shared-webhook env-var fallback.** Read `$SLACK_WEBHOOK_URL` as a
   fallback when `[slack] webhook` is not set in `relay.toml`. The
   conventional name (used by other tools that publish to Slack) is the
   point — multiple apps on the same machine can share one Slack app
   config without each duplicating the URL. Resolution order:
   `relay.toml` value first, then `$SLACK_WEBHOOK_URL`, then the existing
   stderr fallback. Document the convention in
   `src/relay/resources/templates/relay-os/relay.toml` (commented `[slack]`
   block) and the README slack section.
3. **Structured failure path.** Today a network failure during `bump`
   silently disappears into stderr. Append a record to
   `relay-os/.slack-failures.log` (per-project, sibling to `relay.toml`)
   on every failed post (after retries exhaust per (4)). Format: one
   line per failure, tab-separated:
   `<ISO8601 timestamp>\t<exception class>\t<message preview ≤120 chars>`.
   Append-only; no rotation in v1 — the file is meant to be inspected
   and cleared manually after triage. Add `relay-os/.slack-failures.log`
   to `.gitignore`. `relay status` reads the file and, if it exists and
   is non-empty, prints a footer line:
   `⚠ N Slack post failures — see relay-os/.slack-failures.log` (where N
   is the line count). Empty/absent file → no footer, no behavior change.
   Goal: scripted runs can tell whether posts landed.
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

- [ ] `relay validate` reports three distinguishable Slack states when
      a webhook is configured: healthy (empty-text probe returns 400 +
      `no_text`), revoked (404 + `no_service`), unreachable
      (`RequestException`). Exit non-zero on the latter two.
- [ ] Setting `$SLACK_WEBHOOK_URL` with no `[slack]` block in
      `relay.toml` posts successfully through `relay feed` /
      `relay bump`. A `[slack] webhook` value in `relay.toml` overrides
      the env var.
- [ ] A failed `relay bump` post (mechanism: pytest `monkeypatch` of
      `relay.slack.requests.post` to raise
      `requests.exceptions.ConnectionError`) appends a line to
      `relay-os/.slack-failures.log` matching the documented format.
      Tests must not require network access or new dependencies.
- [ ] After such a failure, `relay status` prints the
      `⚠ N Slack post failures — see relay-os/.slack-failures.log`
      footer. With an empty / absent log file, the footer is not
      printed and `relay status` output is byte-identical to today.
- [ ] `relay-os/.slack-failures.log` is listed in `.gitignore`.
- [ ] Tests cover: missing config → stderr; `$SLACK_WEBHOOK_URL` only
      → posts; toml override of env var; retry-then-success
      (`monkeypatch` raises `ConnectionError` twice then returns 200);
      retry exhaustion → log entry written.
- [ ] README + `relay.toml` template comment document
      `$SLACK_WEBHOOK_URL` and the `relay.toml`-takes-precedence rule.
