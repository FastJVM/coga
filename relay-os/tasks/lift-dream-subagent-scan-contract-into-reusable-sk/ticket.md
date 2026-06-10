---
title: Lift Dream subagent-scan contract into reusable skills
status: draft
mode: interactive
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

Dream's Phase 2 (knowledge scan) and Phase 3 (contract audit) each delegate to
a subagent with a ~60-line classification contract inlined in
`relay-os/recurring/dream/ticket.md` and re-emitted verbatim into every
per-period Dream task body. The taxonomy (`extract` / `stale` / `gap` /
`drift`), the corpus to read, the output shape, and the constraints are all
duplicated prose with no source skill to reference.

Lift the two subagent contracts into reusable Relay skills (referenced as
`bootstrap/dream/scan/knowledge-scan` and `bootstrap/dream/scan/contract-audit`):

- `relay-os/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md` —
  the Phase 2 contract.
- `relay-os/bootstrap/skills/bootstrap/dream/scan/contract-audit/SKILL.md` —
  the Phase 3 contract.

Then trim the Dream recurring-task body to point at those skills instead of
re-stating the contract, and confirm Dream still runs the same scans.

Acceptance:

- Both skill files exist as prompt-only skills (frontmatter: `name:` +
  one-sentence `description:`, no `script:` and no `## Known Skill Contract`
  block — those belong to the script-worker skills like `tasks/validate-drift`,
  which is the wrong shape to copy here). Each contains the classification
  taxonomy + corpus list + output shape the Dream body now inlines.
- `relay-os/recurring/dream/ticket.md` references the skills and stops
  repeating the contract. Rule for how much moves: the body keeps only the
  delegate-to-a-subagent framing and the `## Findings` write target; every
  classificatory detail (taxonomy, corpus list, output shape, constraints)
  moves into the skill.
- The packaged copies stay in sync — both the recurring body at
  `src/relay/resources/templates/relay-os/recurring/dream/ticket.md` AND the two
  new skill files under
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/scan/`.
  (The packaged tree already mirrors `bootstrap/skills/bootstrap/dream/tasks/`,
  so the new `scan/` skills must be mirrored too, or the trimmed body will
  reference skills absent from the shipped package.)
- Content-equivalence check (not a behavioral rerun): the contract text the
  subagent receives is unchanged — diff the lifted skill bodies against the
  removed inline prose and confirm the taxonomy, corpus, output shape, and
  constraints are preserved verbatim apart from the delegation framing. A live
  Dream rerun is not required and not reliably reproducible (the scans are LLM
  reads over the live corpus, not a deterministic golden fixture).

This finding came out of the Dream-2026-W21 knowledge scan as gap G1.

## Context

Dream's existing worker skills live under `relay-os/bootstrap/skills/bootstrap/dream/`
— for example `tasks/validate-drift/SKILL.md` and `tasks/cleanup-orphan-markers/SKILL.md`,
referenced from the body as `bootstrap/dream/tasks/<name>`. The two new skills are
subagent *scans* (not deterministic script workers), so they take a new `scan/`
segment alongside the existing `tasks/` segment, but must share the same skills
root. Do **not** create them under a top-level `relay-os/skills/` — that tree is
unrelated.

The inlined contract to lift lives at `relay-os/recurring/dream/ticket.md`:
Phase 2 (knowledge scan) and Phase 3 (contract audit), roughly lines 82–145.
Trim those phases to reference the new skills while preserving the per-phase
delegation framing and the `## Findings` handling downstream. The packaged
mirror at `src/relay/resources/templates/relay-os/recurring/dream/ticket.md` is
currently byte-identical to the live copy and must stay in sync.

Known caveat (don't try to fix it in this ticket): Phase 3's own contract-audit
corpus globs `relay-os/contexts/**/SKILL.md` and `relay-os/skills/**/SKILL.md`,
which do **not** cover `relay-os/bootstrap/skills/…`. So the new scan skills sit
outside the surface the audit reads — the audit won't audit the skills that
define it. That mirrors the existing `tasks/` skills (already outside the glob),
so it's pre-existing, not introduced here. Note it on the blackboard as a
possible follow-up; do not widen the audit glob as part of this change.

