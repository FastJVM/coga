---
title: relay-additions-spec
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: docs/create-google-doc
  steps:
  - name: preflight
    skills: []
    assignee: agent
  - name: draft
    skills: []
    assignee: agent
  - name: revise
    skills: []
    assignee: agent
---

## Description

Produce a Google Doc titled "Relay Additions — Ticket Specs" that rewrites the wishlist items from the relay-additions doc as specs concrete enough to seed future relay tickets: for each item, the behavior described precisely enough that an agent could implement from it (what it does, where it lives in Relay, what done looks like).

## Context

- Doc title: "Relay Additions — Ticket Specs". Audience: spec to seed future tickets — each item written so it could become a relay ticket later.
- **Sequenced: do not launch until the relay-additions task is done.** The specs should reflect the team's reaction to the "Relay Additions" wishlist doc, not spec all items blind. Source material = the shipped "Relay Additions" Doc plus whatever feedback the team gave on it; the raw items live in `relay-os/tasks/relay-additions/ticket.md`.
- Only spec the items that survived team review — ask the human which items made the cut before drafting. Skip re-interviewing for content beyond that; the items themselves are already written.
- Upload to the existing Drive folder "Relay Wishlist/ Bucket Comparison" (ID `1W3cjsWsmMn_OysmjTYIuaoeEF9RRobat`), next to the "Relay Additions" doc.