---
title: Finish Slack integration features
status: draft
mode: interactive
owner: nick
assignee: claude1
skill: bootstrap/ticket
---

## Description

Slack is plumbed but minimal. We suspect parts aren't actually working in
practice and several features are stubs. Audit the current state, identify
gaps, and finish the integration so it's reliable and useful.

## Current state (as of opening)

- `src/relay/slack.py` exposes `post_feed(cfg, message)` and
  `post_mention(cfg, user, message)`.
- Single webhook configured via `[slack] webhook = "..."` in `relay.toml`.
- When no webhook is configured, messages go to `stderr` prefixed with
  `[slack]`. When a post fails, the error also goes silently to stderr.
- Callers today: `bump.py`, `launch.py`, `launch_script.py`, `feed.py`,
  `panic.py`. Each posts FYI or @mention; no threading.

## Known / suspected gaps

- **Verification.** Confirm what actually works end-to-end. `relay
  validate` should fail loudly if `slack.webhook` is set but unreachable.
- **Channel routing.** One webhook = one channel. Different teams /
  contexts / projects may want different channels. Likely: a map in
  `relay.toml` keyed by team or context, with the existing `webhook` as
  default.
- **Threading.** Right now every post is a top-level message. A ticket's
  lifecycle (launch → step → done) should thread under a single root
  post per task. Needs a per-task thread-ts cache (probably in the
  ticket frontmatter or a sibling dotfile).
- **Retry / persistence.** A network blip drops the message. A small
  on-disk queue + retry would make it reliable.
- **Error visibility.** Silent stderr swallowing is fine in dev but
  hides real problems in scripted use. Add a structured failure path
  (log file or `relay status` surface).
- **Inbound.** Today Slack only receives. Some flows (e.g. responding
  to a `panic` alert) might benefit from Slack→relay events. Out of
  scope for this ticket unless trivial.

## Open questions

- Does the codebase need to support multiple Slack workspaces (one per
  team) or just multiple channels in one workspace?
- Webhook vs. bot token: webhook is enough for outbound posts but
  threading needs the chat.postMessage API with a bot token. Trade off
  simplicity vs. functionality.
- Should `relay panic` page a specific on-call user (per-team rotation)
  or only fire `post_mention`?

## Out of scope

- Inbound Slack -> ticket creation (covered by a separate ticket on
  Slack-as-sync).
- Slack-driven retro / knowledge extraction (covered by the retro
  ticket — that one will *use* this integration).

## Why now

The retro ticket (`add-bootstrap-retro-skill-for-knowledge-extraction`)
and the upcoming Slack-as-sync ticket both depend on a working Slack
integration. Finishing this unblocks them.
