---
title: Plan a project into tickets
mode: interactive
skills:
  - bootstrap/project
assignee: claude
---

## Description

Persistent launch target for an interactive project-planning session.

Use `coga project` or `coga launch bootstrap/project` to interview the human
about a project — outcome, prior art, constraints, dependencies — and turn the
answers into an ordered set of `draft` tickets, one per step. Pass a one-line
description or a doc path as `coga project "<seed>"` to seed the interview.

This ticket is stateless. It has no status and acquires no lock — every launch is
independent. Don't edit the ticket itself except to swap the `assignee` to
whichever agent type you have configured in `coga.toml`.

## Context

The actual instruction set lives at
`coga-os/bootstrap/skills/bootstrap/project/SKILL.md` unless a local
`coga-os/skills/bootstrap/project/SKILL.md` override exists. This ticket routes
bare `coga launch bootstrap/project` sessions to that skill — read the skill
if you're debugging the planning flow.

`assignee` must match an `[agents.<type>]` block in `coga.toml`. The default
`claude` assumes the standard install; swap if you've renamed your agent types.

Don't add `status:` or `owner:` to this frontmatter. The ticket is intentionally
stateless — no lock, no log, no `step` transitions — so every launch can run
concurrently with no coordination. That's why it diverges from the canonical
`coga-os/tasks/_template/ticket.md` shape.
