---
name: coga/notifications
description: How Coga decides whether an event posts (surface) and where it lands (destination), where the channel is configured, how owners are pinged, what happens when a post fails, how to respond to a leaked webhook, and why there is no retry or digest.
---

# Notifications

Notifications are the sync point between asynchronous agents and the humans
approving, unblocking, or watching them. Slack is the first channel; Git is
the other sync layer (`coga/sync`).

## Surface and destination are separate decisions

- **Surface** — post or stay silent. Urgent events and explicit FYIs post
  live; ticket outcomes (`done`, `canceled`, recurring errors) post as
  outcomes. Everything else — draft creation, `mark active`, manual pauses,
  message-less `bump`, successful recurring creates, relaunching an
  `in_progress` ticket — is silent; `coga/log.md` and git are the record.
- **Destination** — the ordinary flow webhook (operating awareness, outcomes,
  aggregates) or the important webhook (a human must act; see
  `coga/important`).
- **Cadence** — every post is delivered live, one message per event. There is
  no digest, batch, or spool, so there is no fallback queue: an event either
  posts now or is silent. Importance picks where a delivered post goes, never
  when. Commits that reach `main` without a Done ticket are never announced;
  `git log` and GitHub are the record.

The event-by-event inventory is `coga/notifications/producers`.

## Configuration

The `--- Notification channels ---` comments in the shipped `coga.toml` own
the keys: opting in, `env:` webhook references, the important webhook, GIFs,
the owner-to-Slack-ID map, the local opt-out, and `coga validate
--check-slack`. Notifications are off in a fresh repo. Webhook URLs are
bearer tokens: commit only `env:` references (`coga/secrets`).

## Pinging the owner

Every post carries a `[<project>] [<owner>]` prefix. The owner is the only
addressee — no watcher list, no cc trailer, no separate `--important`
recipient. An incoming webhook cannot look users up, so
`[notification.slack.users]` in shared `coga.toml` maps a Coga name (the
ticket's `owner` token) to a Slack member ID; a mapped owner gets a real
`<@…>` ping, an unmapped one is named in plain text.

## When a post fails

Once Slack is selected and enabled, an unresolved webhook or a delivery miss
(transport error, revoked webhook, non-2xx) is reported on stderr, and a
delivery miss for a ticket also gets a `slack` line in `coga/log.md`. A post
announcing a transition already written — a block, a bump FYI, done or
canceled, a watchdog pause, recurring alerts — reports and returns, because
the markdown is the source of truth. Commands that will post check the
webhook configuration first (a terminal or `--message` bump, `mark done`,
`mark canceled`), so a missing webhook refuses them before the ticket
changes. An important post with no `important_webhook` is refused, never
rerouted to flow. Fix the configuration and rerun.

Coga never prints a raw Slack error, since it would contain the webhook URL.
If a webhook URL or `/services/…` path ever appears in a diagnostic, treat it
as compromised: revoke or rotate it in Slack, redact the tracked
`coga/log.md`, and inspect every reachable commit and other copies (forks,
clones, CI logs, caches). A redaction commit does not erase history;
rewriting and force-pushing published history is a separate destructive step
that needs explicit, coordinated approval and still cannot recall existing
copies.

## No retry

`post` makes one attempt and never retries. A delayed FYI is stale relative
to local state; rerunning the command re-derives the message from current
state. Probe with `coga validate --check-slack` before a batch of work.

How the code implements these rules is in
[notification internals](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/notifications/SKILL.md),
for changing Coga only.
