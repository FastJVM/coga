---
slug: v2/use-slack-as-a-sync-channel-for-tickets
title: Use Slack as a sync channel for tickets
status: draft
mode: agent
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills:
- bootstrap/ticket
workflow: null
---

## Description

Relay is locally operated and git-backed — there's no central server.
This raises a real question: how do tickets propagate between machines,
users, or agents that aren't sharing a working tree?

Idea: **use Slack as the sync wire.** Slack is already in the loop (every
launch / step / done emits there per the Finish-Slack ticket). If we
shape the messages right, the Slack channel itself becomes a durable,
human-readable, append-only log of ticket events that other relay
instances can replay.

Shape is genuinely unclear. This ticket is to **explore options** and
pick one — not to ship a specific design.

## Possible shapes

1. **Slack as event log.** Every meaningful ticket transition (create,
   step, status change, done) is posted as a structured message
   (markdown body + a hidden JSON envelope). A receiving relay polls
   Slack history, deduplicates by event ID, and applies. Like a
   poor-person's CRDT over a chat channel.

2. **Slack-triggered ticket ingestion.** A bot user listens for
   `@relay create "<title>"` mentions and creates tickets in some
   target repo. Lighter — just inbound creation, not full state sync.

3. **Slack as a notification + handoff layer.** No state sync. Slack
   tells you when a ticket needs human attention or when work is
   ready for review on a specific machine; humans pick up the work
   in their local repo via git pull. State stays in git, Slack just
   surfaces it.

## Open questions

- What's the actual user pain we're solving? (Multi-machine on the
  same person? Multiple teammates? Distributed agents?) The answer
  shapes which option fits.
- Is git push / pull the source of truth, with Slack as a notifier
  (option 3), or is Slack itself authoritative for state-not-yet-in-git
  (options 1-2)?
- Auth model: who is allowed to create tickets via Slack? Does the
  bot live per-team, per-workspace, or per-repo?
- Conflict resolution: if two relays both apply the same Slack event
  before sync, what wins? (Probably git's normal merge, but worth
  spelling out.)

## Why now

The Slack integration is being finished separately. Once it's reliable,
it becomes a natural candidate for the sync question — which Relay
otherwise punts on entirely (the locally-operated model has no
multi-machine story today).

## Dependencies

- Blocked on `finish-slack-integration-features` for reliable plumbing
  (especially threading and retry).
- Probably wants a small spike doc before any code lands — pick one of
  the three shapes above (or a fourth) before designing the schema.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
