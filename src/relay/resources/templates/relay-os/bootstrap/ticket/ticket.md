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
