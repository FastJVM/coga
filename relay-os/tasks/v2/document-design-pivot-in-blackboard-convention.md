---
slug: v2/document-design-pivot-in-blackboard-convention
title: Document design-pivot-in-blackboard convention
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
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

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
