---
name: coga/important
description: The coga-important Slack channel — what earns a notification there, how it differs from coga-flow, how scripts raise one with `coga slack --important`, and who is expected to act on it.
---

# coga-important — notifications that need human action

`coga-important` is the Slack channel for notifications that need a human to
act. Nothing else goes there. Coga's automatic state-transition broadcasts —
create, bump, mark — stay in coga-flow.

The two channels split by what the message asks of the reader, not by urgency
or by who sent it. coga-flow is a record: agents moved a ticket, and you read
it when you want to know where things stand. coga-important is a queue: an
unread message there is work nobody has done yet.

## Raising an alert

Any script that detects an action-needed event posts it with `coga slack
--important`. A patent sweep that finds a maintenance fee due raises it that
way, and so does anything else with a real-world consequence behind it.

Alerts land automatically. There is no human step between detecting the event
and posting it — a safety net that only catches what someone remembered to
throw at it is not a safety net.

## Triage

Every `--important` post @'s one recipient: the coga user named by
`[notification.slack].important_recipient` in coga.toml. That user is the
triage owner. Every alert lands on them, whether or not they are the one who
ends up acting.

From there they do one of three things:

- Handle it.
- @ someone in the Slack thread.
- Open a ticket, if it is real work.

Handing off stays a plain Slack @ and gets no coga machinery. A thread reply
keeps the alert's context attached to it; a second `coga slack` post would land
disconnected from the alert it refers to, and add exactly the channel noise
this convention exists to prevent.

## The bar, and why it holds

Two failures pull in opposite directions: being inundated with notifications,
and letting something fall through the cracks. The `--important` bar — a human
must act — is what holds the middle.

The bar is worth defending because widening it fails in both directions at
once. A channel that collects things worth knowing becomes a feed people tune
out, and then the alert that did need a human is missed inside it. That is the
second failure arriving through the first.

This is why a blocker is not an `--important` post, even though it plainly
needs a human. `coga block` notifies the ticket owner through the normal path,
and the ticket itself is already the queue — the blocker is attached to it and
cannot be lost. An alert has no ticket, which is the whole reason it needs a
channel.

## What this context does NOT cover

- How notifications reach Slack at all, the live/digest tiers, and git sync —
  `coga/sync`.
- Configuring the channel. `[notification.slack].important_webhook` and
  `important_recipient` are coga.toml keys; see `coga/sync`.
- What any given script should treat as action-needed. That judgment belongs to
  the script and its own context.
