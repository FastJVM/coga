---
title: Add an always-on context tier composed into every launch
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills:
- bootstrap/ticket
workflow: null
---

## Description

Today, contexts are composed into a launch only when a ticket lists them
in its `contexts:` frontmatter. The canonical `relay/*` contexts get there
either because the bootstrap shim lists them (e.g. `bootstrap/orient`) or
because a ticket explicitly cites them. There's no way for a repo to say
"every launch in this repo should always carry context X" without editing
every ticket.

This ticket adds a new tier: an *always-on* set of contexts that compose
into every launch alongside whatever the ticket explicitly lists. The
relay canon (`architecture`, `principles`, `cli`) ships in there by
default. Per-repo extensions live alongside.

Pairs with: `add-extend-ticket-format-skill`. That skill writes its
output into the always-on tier so every future ticket launch carries
the new field semantics as part of the ambient prompt.

## Open questions

- **Where the list lives.** Three candidates:
  - *Directory convention.* `relay-os/contexts/_always/<name>/SKILL.md`
    — anything inside is auto-included. Markdown-first, one place to
    see what's always loaded. Matches the `_template/` prefix
    convention already in use under `relay-os/tasks/`.
  - *`relay.toml` list.* `[compose] defaults = ["relay/architecture", ...]`
    — more explicit; a context can be in the canon dir and *not* in the
    always set.
  - *Per-context frontmatter flag.* `always: true` on the context's
    SKILL.md frontmatter. Distributed — harder to see the full default
    set at a glance.
  - Default to the directory convention unless a reason surfaces.
- **Does `relay init` seed it?** Cleanest: seed `_always/` with the
  relay canon (architecture, principles, cli) so they're visible and
  editable per-repo. Alternative: keep the relay canon hardcoded and
  let `_always/` hold repo additions only. Seeded is more legible —
  matches "fail loud, never silent magic."
- **Compose pipeline order.** New tier slots in between repo context
  and ticket-specific contexts:
  - Rules → Repo context → **Always-on contexts** → Ticket `contexts:`
    → Step skill → Blackboard → Ticket body
- **Token cost.** Always-on contexts load on every launch. `relay
  launch --prompt-report` already exists as the guardrail — a repo
  with 10 always-on contexts will see the cost there.
- **Interaction with `bootstrap/orient`.** Orient currently lists the
  relay canon explicitly. Once `_always/` seeds those, orient should
  stop listing them to avoid double inclusion.

## Context

- Compose pipeline: `src/relay/compose.py`.
- Existing context layer doc: `relay-os/contexts/relay/architecture/SKILL.md`
  under "Prompt composition".
- Prompt-cost guardrail: `relay launch <slug> --prompt-report`.
- Bootstrap shim for orient: `relay-os/bootstrap/orient/ticket.md`.
