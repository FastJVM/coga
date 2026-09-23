---
name: coga/notifications
description: How Coga decides whether an event posts (surface), where it lands (destination), how the notification channel is configured, opted into, and out of, how owners are pinged, how messages are formatted, and why there is no retry or digest.
---

# Notifications

Notifications are the sync point between asynchronous agents and the humans
approving, unblocking, or watching them. Slack is the first backend behind the
channel-agnostic surface in `src/coga/notification/__init__.py`; it is not
the whole abstraction. Git is the other sync layer (`coga/sync`).

## Surface and destination are separate decisions

- **Surface** — post or stay silent. `notification.post` is the live path for
  urgent events and explicit FYIs. `notification.notify` is the outcome path:
  it accepts only the kinds in `OUTCOME_EVENT_KINDS` (`done`, `canceled`,
  `recurring-error`) and raises `ValueError` for anything else, which keeps it
  from becoming a second general broadcaster. Everything else — draft
  creation, `mark active`, manual pauses, message-less `bump`, successful
  recurring creates, relaunching an `in_progress` ticket — is silent;
  `coga/log.md` and git are the record.
- **Destination** — the ordinary flow webhook (operating awareness, outcomes,
  aggregates) or the important webhook (a human must act; see
  `coga/important`).
- **Cadence** — every post is delivered live, one message per event. There is
  no digest, batch, or spool (the daily digest was removed, #786), so there
  is no fallback queue: an event either posts now or is silent. Importance
  picks where a delivered post goes, never when. Commits that reach `main`
  without a Done ticket are never announced; `git log` and GitHub are the
  record.

The event-by-event inventory is `coga/notifications/producers`. Failure
semantics, the `preflight_post` gate, and redaction are
`coga/notifications/failures`.

## Configuration

```toml
[notification]
channels = ["slack"]

[notification.slack]
webhook = "env:SLACK_WEBHOOK_URL"
important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
```

- **Optional on first run.** `coga init` writes `channels = []`, so a new
  repo runs `create`/`mark`/`launch`/`bump` with nothing configured; `post`
  writes one `[notification] no channels configured` stderr line and
  returns. When `[notification].channels` is absent, Slack is inferred only
  from a `[notification.slack]` table. Unknown channel names fail config load.
- **Fail loud once selected.** With Slack selected and
  `[notification.slack].enabled` true (the default), an unresolved webhook
  or a delivery miss is surfaced, never dropped quietly
  (`coga/notifications/failures`).
- **Webhooks are bearer tokens.** Commit only `env:` references (resolved by
  `config._resolve_secret_value`; see `coga/secrets`). A bare exported
  `SLACK_WEBHOOK_URL` with no `webhook` key fails config load with guidance;
  a literal URL parses but must never be committed. `enabled`, `webhook`,
  and `important_webhook` each resolve with `coga.local.toml` overriding the
  shared file.
- **Opt-out is an exit, not a default.** `[notification.slack].enabled =
  false` in `coga.local.toml` suppresses every Slack call to one stderr line
  (`[slack] disabled (post suppressed): …`) and never crashes. It exists for
  solo, dev, test, and CI runs; the cost is leaving the team's sync loop.
- **GIFs.** `[notification.slack.gifs]` may attach a random GIF per event
  kind (`done`, `block`); omit a kind to stay text-only.
- **Checks.** Default `coga validate` does no network I/O and warns when
  Slack is selected and enabled but `important_webhook` is unresolved (the
  opt-out suppresses the warning). `coga validate --check-slack` probes the
  primary webhook with an empty-text payload Slack rejects without posting,
  and is skipped under the opt-out.

## Pinging the owner

Every post carries the `[<project>] [<owner>]` prefix from
`SlackChannel.render_text`. The owner is the only addressee — no watcher list,
no cc trailer, no separate `--important` recipient. An incoming webhook cannot
look users up, so `[notification.slack.users]` in shared `coga.toml` maps a
Coga name (the ticket's `owner` token) to a Slack member ID; `mention` emits
`<@U…>` for a mapped name and plain text otherwise. Member IDs are not
secret.

## Message format

Message strings are built at the call sites (`commands/*.py`, `autoclose.py`,
…); `post`/`notify` never reformat. For per-ticket posts:

- The owner is the prefix; never add an in-text `(owner: …)`.
- The title is always present: `*{slug}* "{title}"`.
- `→` is a transition and shows the prior state (`{prev} → {new}`, or
  `{prev} → done`); a workflow-less done post collapses to "finished".
- `:` introduces the body, `(key: value)` is an aside, and `—` is reserved
  for the optional trailing FYI (`bump --message`, pause reasons, retire
  notes).
- PR references are Slack links, `<{url}|PR #{N}>`.

`tests/test_notification_messages.py` snapshots the formats; extend it when a
string changes.

## No retry

`post` makes one attempt (5-second request timeout) and never retries (#56
removed backoff). A delayed FYI is stale relative to local state; rerunning
the command re-derives the message from current state. Probe with
`coga validate --check-slack` before a batch of work.

## Adding a notifying command

Decide, in order: the surface (`post`, `notify`, or silence); the destination
(important only when a human must act and no human-owned ticket already holds
the ask); and the preflight policy (`coga/notifications/failures`).

Delivery is outbound only today. Nothing in the `post` API precludes inbound
replies or slash commands later, so do not bake in one-way assumptions.
