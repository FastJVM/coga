---
title: Lift Dream subagent-scan contract into reusable skills
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

Dream's Phase 2 (knowledge scan) and Phase 3 (contract audit) each delegate to
a subagent with a ~60-line classification contract inlined in
`relay-os/recurring/dream/ticket.md` and re-emitted verbatim into every
per-period Dream task body. The taxonomy (`extract` / `stale` / `gap` /
`drift`), the corpus to read, the output shape, and the constraints are all
duplicated prose with no source skill to reference.

Lift the two subagent contracts into reusable Relay skills:

- `bootstrap/dream/scan/knowledge-scan/SKILL.md` — the Phase 2 contract.
- `bootstrap/dream/scan/contract-audit/SKILL.md` — the Phase 3 contract.

Then trim the Dream recurring-task body to point at those skills instead of
re-stating the contract, and confirm Dream still runs the same scans.

Acceptance:

- Both skill files exist, frontmatter follows the standard SKILL.md shape, and
  each contains the classification taxonomy + corpus list + output shape the
  Dream body now inlines.
- `relay-os/recurring/dream/ticket.md` references the skills and stops
  repeating the contract.
- The packaged copy at
  `src/relay/resources/templates/relay-os/recurring/dream/ticket.md` stays in
  sync.
- A Dream rerun behaves identically (same findings on the same fixture).

This finding came out of the Dream-2026-W21 knowledge scan as gap G1.

## Context

