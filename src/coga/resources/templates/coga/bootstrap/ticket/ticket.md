---
title: Create a new ticket
skills:
  - bootstrap/ticket
agent: claude
---

## Description

Persistent launch target for an interactive ticket-authoring session.

Use `coga create "<title>"` when you already know the task title and want raw
draft bytes immediately. Use `coga ticket` or `coga launch bootstrap/ticket`
when you want the skill to interview the human first; the skill can scaffold a
draft with `coga create` and then edit it.

This ticket is stateless. It has no status and acquires no lock — every
launch is independent. Don't edit the ticket itself.

## Context

The actual instruction set lives at
package `bootstrap/skills/bootstrap/ticket/SKILL.md` resources unless a local
`coga/skills/bootstrap/ticket/SKILL.md` override exists. This ticket routes
bare `coga launch bootstrap/ticket` sessions to that skill — read the skill if
you're debugging the bootstrap flow.

`agent:` here is the install-level default and last resort for which agent
runs a `coga ticket` or megalaunch picked-draft authoring interview. It
governs the bare `coga ticket` interview and any target ticket without its
own `agent:`; a target's `agent:` wins over it. It must name an effective
`[agents.<type>]` block after `coga.local.toml` layers over `coga.toml`. To
change it for the whole install, add a local `coga/bootstrap/ticket/ticket.md`
(it overrides this packaged copy).

To switch the authoring agent for one run or one session — for example while
one agent's quota is exhausted — don't edit this file. Use, highest first:
`coga ticket --agent <name>` (or `coga megalaunch --agent`),
`coga ticket --pick-agent`, `COGA_AUTHORING_AGENT=<name>`, or
`[authoring] agent = "<name>"` in `coga.local.toml`. The `coga/tickets`
context owns the full order. A direct `coga launch bootstrap/ticket` reads
none of these; it launches with this ticket's `agent:` unless given `--agent`.

Don't add `status:` or `owner:` to this frontmatter. The ticket is
intentionally stateless — no lock, no log, no `step` transitions — so
every launch can run concurrently with no coordination. That's why it
diverges from the canonical `coga/tasks/_template/ticket.md` shape.
