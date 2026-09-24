---
title: Carry the apply-the-register-amendment step in a workflow
status: draft
owner: nicktoper
agent: claude
contexts: []
skills: []
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
secrets: null
step: 1 (agent-produces)
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


The blackboard is a notepad to be written to often as the human and agent works through a task.
