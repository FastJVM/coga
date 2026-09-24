---
title: Repair ticket referents when a referent is renamed or canceled
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

Nothing repairs a ticket's referents when the thing it points at is renamed,
superseded, or canceled. The pointing ticket keeps naming a referent that no
longer means what it did, and a launch gate can name a canceled ticket as a
required precondition — which stops the gate from ever being satisfiable.

Add the repair path: a rule in `coga/skills/tickets/launch-gates/SKILL.md`, a
sweep, or a step that runs at cancel/rename time.

## Context

Raised by the Dream 2026-W36 knowledge scan (Phase 2, shard-09) as a `gap`.

Five live findings in the same run are instances of it:
`resolve-three-stale-multiply-context-claims-flagge` is gated on a canceled
ticket; `v1/communication/doc`'s launch gate names a canceled ticket as a
required referent; `multiply/v1-architecture` names the canceled
`v1/2-self-update` as a live downstream owner; and two `v1/updater/*` drafts
still cite an abandoned design. The pattern is not rare.

### Dream 2026-W39 recheck

The first remedy listed above already exists: `coga/skills/tickets/launch-gates/SKILL.md`
step 4 of "Checking a gate at launch" (added 2026-08-31, commit `80dd373`)
makes a canceled or superseded referent a *broken* gate, tells the agent to
find the successor via the cancel message in `coga/log.md` and rewrite the gate,
and otherwise `coga block` with a "launch gate broken" reason — extended to
renamed, split, or spec-of-record referents. What remains undelivered is the
second and third options only (a sweep, or a repair step at cancel/rename time
that fixes the *pointing* tickets). Narrow the ask to that half. The
`resolve-three-stale-multiply-context-claims-flagge` example cited in
`## Context` has since been resolved on `main`.

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.
