---
title: Create a new ticket
mode: interactive
skill: bootstrap/ticket
assignee: claude1
---

## Description

Persistent launch shim. Three ways to invoke the bootstrap/ticket skill:

- `relay create "<title>"` — the human-facing entry point. Relay
  scaffolds a new `draft` task seeded from this shim's frontmatter and
  auto-launches the skill on it to fill in workflow, contexts, assignee,
  description.
- `relay launch bootstrap/ticket "<title>"` — equivalent factory form,
  useful when scripting against the shim directly.
- `relay launch bootstrap/ticket` — empty authoring session inside this
  shim. The skill interviews the human, then calls `relay create` itself
  once it has enough to scaffold.

This shim is stateless. It has no status and acquires no lock — every
launch is independent. Don't edit the ticket itself except to swap the
`assignee` to whichever agent nickname you have configured in `relay.toml`.

## Context

The actual instruction set lives at
`relay-os/skills/bootstrap/ticket/SKILL.md`. This shim just routes
`relay create` and `relay launch bootstrap/ticket` to that skill — read
the skill if you're debugging the bootstrap flow.

`assignee` must match a key under `[assignees.<human>.agents]` in
`relay.toml`. The default `claude1` assumes the standard install; swap if
you've renamed agent nicknames.

Don't add `status:` or `owner:` to this frontmatter. The shim is
intentionally stateless — no lock, no log, no `step` transitions — so
every launch can run concurrently with no coordination. That's why it
diverges from the canonical `relay-os/tasks/_template/ticket.md` shape.
