---
title: Create a new ticket
mode: interactive
skills:
  - bootstrap/ticket
assignee: claude1
---

## Description

Persistent launch shim for an interactive ticket-authoring session.

Use `relay draft "<title>"` when you already know the task title and want raw
draft bytes immediately. Use `relay ticket` or `relay launch bootstrap/ticket`
when you want the skill to interview the human first; the skill can scaffold a
draft with `relay draft` and then edit it.

This shim is stateless. It has no status and acquires no lock — every
launch is independent. Don't edit the ticket itself except to swap the
`assignee` to whichever agent nickname you have configured in `relay.toml`.

## Context

The actual instruction set lives at
`relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` unless a local
`relay-os/skills/bootstrap/ticket/SKILL.md` override exists. This shim routes bare
`relay launch bootstrap/ticket` sessions to that skill — read the skill if
you're debugging the bootstrap flow.

`assignee` must match a key under `[assignees.<human>.agents]` in
`relay.toml`. The default `claude1` assumes the standard install; swap if
you've renamed agent nicknames.

Don't add `status:` or `owner:` to this frontmatter. The shim is
intentionally stateless — no lock, no log, no `step` transitions — so
every launch can run concurrently with no coordination. That's why it
diverges from the canonical `relay-os/tasks/_template/ticket.md` shape.
