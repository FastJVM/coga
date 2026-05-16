---
title: Add bootstrap/extend-ticket-format skill for per-repo field extensions
status: draft
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts: []
skills:
- bootstrap/ticket
workflow: null
---

## Description

A repo eventually needs a ticket frontmatter field that the base relay
format doesn't cover — `customer:`, `severity:`, `linear_issue:`,
whatever fits the domain. Today the only path is "edit a context
manually and remember to update every consumer." That's fragile and
undiscoverable.

This ticket adds an interactive bootstrap shim: `relay launch
bootstrap/extend-ticket-format`. The skill interviews the human about
the field they want to add (name, allowed values, semantics, who's
expected to read or write it), then emits a new context describing the
extension into the always-on context tier so every future ticket
launch carries the extension as part of the ambient prompt.

Pairs with: `add-always-on-context-tier`. The output of this skill is
meaningless without the always-on tier — it's what guarantees the new
field's docs reach every agent regardless of which workflow step is
active.

## Open questions

- **Output shape.** One context per extension, or one consolidated
  "this repo's ticket field extensions" context that the skill appends
  to? Per-field is grep-able and lets a repo delete an extension by
  removing a directory. Default: per-field, e.g.
  `relay-os/contexts/_always/ticket-field-customer/SKILL.md`.
- **Reserved-name collision check.** Before writing, refuse field
  names that collide with the canonical set (`title status mode owner
  human agent assignee watchers workflow step contexts skill`). Fail
  loud, point at the canon doc.
- **Update vs. add.** Running the skill twice for the same field —
  refuse with "field X already declared at <path>"? Probably yes;
  humans edit the context file directly to revise.
- **Should it also seed an example ticket?** Tempting — the context
  body could include an inline frontmatter example, *or* the skill
  could scaffold a real draft ticket using the new field. Inline
  example is simpler and avoids creating ticket noise.
- **What does the context body look like?** Minimum: field name,
  allowed values / shape, one-paragraph semantics, who reads it,
  what agents should do when they see it. The skill's job is to ask
  enough questions to fill those in.

## Context

- Bootstrap shim convention: `relay-os/bootstrap/<name>/ticket.md`.
- Existing bootstrap skill to model on: `relay-os/skills/bootstrap/ticket/SKILL.md`.
- Always-on tier (paired ticket): writes go to wherever that ticket
  lands the convention.
- Canonical reserved names live in `relay-os/contexts/relay/architecture/SKILL.md`.
