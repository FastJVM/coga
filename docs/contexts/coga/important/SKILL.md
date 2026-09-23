---
name: coga/important
description: The coga-important destination — the action-needed bar that earns a post there, how it differs from the flow feed, how scripts raise one with `coga slack --important`, and how the task owner triages it.
---

# coga-important — notifications that need human action

`coga-important` is the channel behind `[notification.slack].important_webhook`
for notifications that need a human to act. Nothing else goes there.
Everything else Coga posts — explicit FYIs, urgent exceptions, ticket
outcomes — stays on the flow webhook, and routine lifecycle churn is not
posted at all ([`coga/notifications`](../notifications/SKILL.md)). Being
sent by Coga does not make a post important.

The two destinations split by what the message asks of the reader, not by
urgency or sender. Flow is the operating feed: read it for awareness. Important
is a queue: an unread message there is work nobody has done yet.

## Raising an alert

A script that detects an action-needed event posts it with
`coga slack --task <target> --message "…" --important`. A patent sweep that
finds a maintenance fee due raises it that way, as does anything else with a
real-world consequence behind it. Alerts land automatically: a safety net that
only catches what someone remembered to throw at it is not a safety net.

Unattended machine failures meet the same bar when the only ticket is a
generated recurring period task that no human treats as their queue. Coga
therefore routes these to important: a recurring period's `ticket.py`
exiting non-zero, a completed period that did not advance its declared state,
recurring template parse errors, and watchdog timeouts (plus their
re-escalations). Importance chooses where a delivered alert goes, never when:
every one posts live. The producer inventory is
[`coga/notifications/producers`](../notifications/producers/SKILL.md).

An important post with no resolved `important_webhook` is refused, never
rerouted to flow; whether that refusal aborts the caller is covered in
[`coga/notifications/failures`](../notifications/failures/SKILL.md).

## Triage

Every important post @'s the owner of the task it is raised under — the same
`[project] [owner]` mention every Coga post carries (`SlackChannel.render_text`).
There is no separate recipient setting. The owner is the triage point whether
or not they end up acting, and does one of three things:

- handle it;
- @ someone in the Slack thread;
- open a ticket, if it is real work.

Handing off stays a plain Slack @ with no Coga machinery. A thread reply keeps
the alert's context attached; a second `coga slack` post would land
disconnected from it and add exactly the noise this convention prevents.

## The bar, and why it holds

Two failures pull in opposite directions: being inundated, and letting
something fall through the cracks. The bar — a human must act — holds the
middle. Widening it fails both ways at once: a channel of things worth knowing
becomes a feed people tune out, and the alert that did need a human is missed
inside it.

That is why a blocker is not an important post even though it needs a human.
`coga block` notifies the owner on flow, and the ticket itself is already the
queue — the blocker is attached to it and cannot be lost. An alert has no
ticket, which is the whole reason it needs a channel.

## Not covered here

- What a given script should treat as action-needed — that judgment belongs to
  the script and its own context.
- Webhook configuration and the `coga validate` warning for an unresolved
  `important_webhook` — `coga/notifications`.
