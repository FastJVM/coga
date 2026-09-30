---
title: Carry the apply-the-register-amendment step in a workflow
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: report-to-coga
    skills: []
    assignee: agent
step: 2 (human-owns-and-finishes)
---

## Description

When a ticket amends a signed-off decision register, nothing carries the step
that applies the amendment back to the context. The contexts therefore drift
behind the tickets that amend them.

Add the carrier: either a new skill invoked at the right workflow step, or an
explicit step in a `code/*` workflow that applies register amendments before
the ticket closes.

## Context

Raised by the Dream 2026-W36 knowledge scan (Phase 2, shard-03) as a `gap`.

The Dream 2026-W36 contract audit (Phase 3) independently produced four
`drift` findings that are all instances of exactly this failure — amendments
recorded historically in the retired telemetry parent ticket and now preserved
in `multiply/v1-telemetry-contract` that were never applied to
`multiply/data-handling`, `multiply/commercial-model`, or
`multiply/v1-architecture`. That audit evidence is the strongest argument for
this ticket and is worth reading first.

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise. Dropped the `multiply/v1-telemetry-contract` context ref (multiply-only; the body names it as the motivating example).


## Dev

branch: carry-knowledge-amendments
(local only, one commit a35b5314b, not pushed)

## Draft (agent-produces, 2026-09-30)

Decision (owner, attended session): fold the carrier into the existing code
skills rather than add a new skill/workflow step. Rejected: a standalone
`knowledge/apply-amendments` step before open-pr (extra launched session per
ticket, own branch contract).

Framing: "decision register" is a multiply convention; the generic Coga rule
it breaks is `coga/knowledge`'s sync rule, which had no executing step.
Motivating evidence read in ~/Code/multiply: `multiply/v1-telemetry-contract`
carries dated owner amendments (2026-09-14/16/24/28) never carried to
`data-handling`, `commercial-model`, `v1-architecture`.

Changes on the branch (live + packaged twins byte-identical):
- `code/implement`: new step 7 "Apply knowledge amendments to their owners"
  (edit owning topic + twin, grep and fix siblings, move ticket-held rulings
  into owners, record `knowledge:` under `## Dev`); later steps renumbered
  8-11, step-4 cross-ref updated; one acceptance line.
- `code/self-qa`: step-2 check that makes a missing/unpropagated amendment a
  must-fix finding; one acceptance line.
- `coga/knowledge` sync rule: names these two skills as its carrier for
  `code/*` workflows.

Verification: `.venv/bin/python -m pytest -q tests/test_packaging.py` -> 23
passed (system `python` lacks tomlkit; use the venv).

Weak spots for the owner to judge:
- Judgment-only; no mechanical check (a `knowledge:` line is not validated
  by `coga bump`). Adding `requires:`-style enforcement would touch core.
- Covers `code/*` only. Owner-led decide/design tickets on draft-for-human
  (how multiply's amendments were actually made) are not carried; the
  multiply-side fix would be a line in `multiply/decision-register-style`
  "Before committing a register edit" (grep dependents) — not done here.
- Does not repair the four existing multiply drift findings.
