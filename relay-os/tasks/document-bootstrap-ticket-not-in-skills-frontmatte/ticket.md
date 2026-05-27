---
title: Document bootstrap/ticket-not-in-skills-frontmatter rule
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
---

## Description

Surfaced by Dream W22 Phase 2 knowledge scan (G7).

Six open draft tickets currently carry `skills: [bootstrap/ticket]` in their
frontmatter (`add-always-on-context-tier`,
`add-browser-skill-for-automating-tasks-click-test`, `autotrigger-ticket-type`,
`pass-secrets-to-skills-with-per-skill-scope`,
`token-budget-aware-idle-execution-of-low-priority`,
`use-slack-as-a-sync-channel-for-tickets`). The `skills:` field is for
ticket-level skills, but `bootstrap/ticket` is the authoring interview and
only makes sense when launched via `relay ticket` (or its launch shim).

The `bootstrap/ticket` SKILL.md step 5 even tells authors to remove this when
found ("Modern `relay ticket` injects this skill only into the prompt; it
should not persist on normal tasks"). But that rule is buried in one skill
body — no architecture-level guidance.

Draft outline:

- Add one sentence under
  `relay-os/contexts/relay/architecture/SKILL.md`'s "Primitives" or "Canonical
  ticket frontmatter": `skills:` is for ticket-level skill refs and should
  never carry `bootstrap/ticket` — that skill is launched via the shim, not
  attached to a ticket.

## Context

