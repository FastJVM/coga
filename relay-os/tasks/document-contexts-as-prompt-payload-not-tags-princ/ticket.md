---
title: Document contexts-as-prompt-payload-not-tags principle
status: draft
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
step: 1 (implement)
---

## Description

Surfaced by Dream W22 Phase 2 knowledge scan (G6).

The done ticket `measure-relay-prompt-scope-and-agent-precision`'s final
blackboard captures a load-bearing correction: ticket creation should not
attach broad contexts as labels. It should select exact context payload that
must be included, and process knowledge should stay in workflow step `skill:`
refs. The 35.8 KiB → 25 KiB prompt-size delta is concrete evidence the pattern
matters.

This correction now lives only inside `bootstrap/ticket`'s body. It is a
domain fact about prompt composition, not just process for ticket-authoring,
and it generalizes — agents touching contexts directly (Dream's own contract
audit found bootstrap/orient violating it) need it where they look first,
which is the relay architecture context.

Draft outline:

- Add a heading **"Contexts are prompt payload, not tags"** under
  `relay-os/contexts/relay/architecture/SKILL.md`'s prompt-composition
  section, or open a new `relay-os/contexts/relay/prompt-scope/SKILL.md`.
- 3 bullets: attach only contexts whose body the agent must read; copy a
  single fact into `## Context` rather than attaching the whole context;
  skills attach via workflow steps, not `contexts:`.

## Context

