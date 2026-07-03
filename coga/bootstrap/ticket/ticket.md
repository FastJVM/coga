---
title: Create a new ticket
mode: agent
skills:
  - bootstrap/ticket
assignee: claude
---

## Description

Persistent launch target for an interactive ticket-authoring session.

Use `coga create "<title>"` when you already know the task title and want raw
draft bytes immediately. Use `coga ticket` or `coga launch bootstrap/ticket`
when you want the skill to interview the human first; the skill can scaffold a
draft with `coga create` and then edit it.

This ticket is stateless. It has no status and acquires no lock — every
launch is independent. Don't edit the ticket itself except to swap the
`assignee` to whichever agent type you have configured in `coga.toml`.

## Context

The actual instruction set lives at
`coga/bootstrap/skills/bootstrap/ticket/SKILL.md` unless a local
`coga/skills/bootstrap/ticket/SKILL.md` override exists. This ticket routes bare
`coga launch bootstrap/ticket` sessions to that skill — read the skill if
you're debugging the bootstrap flow.

`assignee` must match an `[agents.<type>]` block in `coga.toml`. The
default `claude` assumes the standard install; swap if you've renamed
your agent types.

Don't add `status:` or `owner:` to this frontmatter. The ticket is
intentionally stateless — no lock, no log, no `step` transitions — so
every launch can run concurrently with no coordination. That's why it
diverges from the canonical `coga/tasks/_template/ticket.md` shape.
