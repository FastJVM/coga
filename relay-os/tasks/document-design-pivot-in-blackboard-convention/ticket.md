---
title: Document design-pivot-in-blackboard convention
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

Surfaced by Dream W22 Phase 2 knowledge scan (G8).

The done ticket `move-automerge-out-of-relay-status` captures a recurring
pattern: a draft is partly designed, then a major pivot happens, the ticket's
`## Description` is rewritten while the blackboard preserves the prior design
under a heading like `## Design decision (date) — SUPERSEDES the X plan`.
Several open drafts (`autotrigger-ticket-type`,
`debug-surface-for-recurring-tasks-streamed-output`) carry the same pattern
with "Open threads for next session" or "Design pivot" headings inline.

The convention exists in practice but is undocumented. `dev/code` only
documents the `## Dev` section. Document the pivot-trail convention so future
ticket authors know where ditched directions go and can write them in a
findable shape.

Draft outline:

- Add section **"Design pivots and superseded plans"** to
  `relay-os/contexts/dev/code/SKILL.md` (or a new
  `relay-os/contexts/relay/blackboard-conventions/SKILL.md`).
- 2-3 bullets: ticket body is current intent only; superseded design lives in
  blackboard under a dated `## Design decision ... — SUPERSEDES X` heading; a
  `> Design pivot (date):` callout in the ticket body points readers at the
  trail.

## Context

