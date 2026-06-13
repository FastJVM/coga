---
title: Rename slack to a notification system with pluggable channels
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Relay treats Slack as *the* sync channel, but Slack is really just the
**first channel** of a notification system. Once the digest work lands
("Digest" already implies delivery-agnostic batching), email and other
channels are the obvious next step. The naming should reflect that: the
delivery layer is **notification**, and Slack is one backend behind it.

**Goal:** rename and reshape the Slack module into a channel-agnostic
notification layer, with Slack as the first pluggable channel — so adding
email later is a new backend, not a rewrite.

### Shape

- `src/relay/slack.py` → `src/relay/notification.py` (or a
  `notification/` package). A channel-agnostic entrypoint —
  `notify(event, *, urgency, owner, watchers, ...)` — selects the
  configured channel(s) and dispatches.
- Slack-specific bits (`_mention`, webhook POST, message rendering,
  milestone GIFs) move behind a `SlackChannel` backend implementing a small
  channel interface (e.g. `send(text, *, image=None)` + how it renders
  mentions). Email etc. become sibling backends later.
- Config: `[slack]` → `[notification]` with a `channels = [...]` list and
  per-channel sub-tables (`[notification.slack]` carrying webhook + users +
  gifs). Keep back-compat: read legacy `[slack]` and `$SLACK_WEBHOOK_URL`
  with a deprecation note so existing repos don't break.
- Preserve current semantics exactly: crash-loud-by-default on failure,
  no-retry, enabled-by-default, `[<project>] [<owner>]` prefix, watcher cc.
  This is a rename + indirection, not a behavior change.

### Touchpoints

- `src/relay/slack.py` (rename/restructure) and every `post()` call site:
  `commands/create.py`, `bump.py`, `mark.py`, `commands/retire.py`,
  `commands/recurring.py`, `commands/panic.py`, `commands/launch_script.py`,
  `commands/slack.py`. (The `relay slack` command keeps working — alias to
  the manual-notify path.)
- `config.py` — `[notification]` schema + `[slack]` back-compat shim.
- Context: revise `relay/sync` (and `relay/architecture` where it calls
  Slack "the sync point") to describe notification-with-channels, Slack as
  channel #1. Mirror the packaged copy under
  `src/relay/resources/templates/relay-os/`.
- Init: `commands/init.py` Slack-setup hint generalizes to channels.
- Tests: rename `tests/test_slack*`; add channel-dispatch + back-compat
  coverage. Update `example/relay-os/` config.

### Non-goals

- Actually implementing the email (or any non-Slack) channel — this ticket
  only establishes the abstraction and moves Slack behind it. Email is a
  follow-up that adds one backend.
- Changing the crash-loud / no-retry failure policy.

### Open questions

- Module vs package (`notification.py` vs `notification/` with a backend
  per file).
- Config shape: flat `[notification]` + `channels=[...]`, vs nested
  `[notification.<channel>]` tables — and how long to keep the `[slack]`
  shim.
- Whether `relay slack` keeps its name or gains a `relay notify` spelling
  (alias either way).

### Related

- `stop-overloading-relay-slack` — the digest; should build against the
  notification interface rather than `slack.post` from the start.
  Sequencing: ideally this rename lands first (or they co-develop) so the
  digest targets the new surface.
- `rewrite-slack-messages`, `use-slack-as-a-sync-channel-for-tickets`,
  `slack-post-ignores-http-response-so-bad-webhook-fa`,
  `slack-webhook-is-env-only-despite-toml-comment-imp`,
  `post-slack-notification-on-mode-script-failures` — existing Slack tickets
  this rename touches or subsumes; review for overlap during authoring.

## Context

The notification layer's contract lives in `relay/sync`
(§"Slack — the team sync point") and `relay/architecture`. Current
implementation: `src/relay/slack.py` + `[slack]` config in `config.py`.
