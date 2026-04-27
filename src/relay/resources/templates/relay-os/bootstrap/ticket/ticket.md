---
title: Create a new ticket
mode: interactive
skill: bootstrap/ticket
assignee: claude1
---

## Description

Persistent launch shim. Two ways to invoke it:

- `relay launch bootstrap/ticket` — empty authoring session. The skill
  interviews the human, scaffolds a task, fills in the frontmatter.
- `relay launch bootstrap/ticket "<title>"` — factory mode. Relay scaffolds
  a new design-status task with that title (seeded from this shim's
  frontmatter), then launches the agent on it to fill in workflow,
  contexts, assignee, description.

This shim is stateless. It has no status and acquires no lock — every
launch is independent. Don't edit the ticket itself except to swap the
`assignee` to whichever agent nickname you have configured in `relay.toml`.
