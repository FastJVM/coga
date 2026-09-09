---
slug: phase-0-audit-is-complete-per-the-plan-but-still-i
title: phase-0-audit is complete per the plan but still in_progress
status: draft
owner: nicktoper
human: nicktoper
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
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`coga/contexts/marketing/plan/SKILL.md` lists `marketing/phase-0-audit` under
"Execution tickets and disposition" as "complete input to this plan; do not
rerun it", and the plan has already absorbed the audit's output — its Phase 0
gate table matches the ticket's `## Proposed phase-1 thresholds` almost line for
line, and the plan's "only publishable narrative evidence is Coga operating on
Coga" absorbs the ticket's `## Plan premise failure`.

The ticket itself is still `status: in_progress` at `step: 2 (human-owns-and-finishes)`.
Its `draft-for-human` step 3 (`report-to-coga`) has therefore never run, and
because it is not `done` it will never be reaped by Dream's done-ticket sweep —
it sits in `coga status` as live work indefinitely. This Dream run's
validate-drift pass also flags it as `stuck-in-progress`, idle for ~139 hours.

The two statements disagree about whether the audit is finished, and one of them
should change.

## Context

Either close the ticket — its substance is now carried by the plan context plus
the nine `cleanup/` tickets it produced — or drop the plan's "complete input"
claim and let the audit finish its own step 3.

Closing is the likelier intent, but it is a lifecycle call on a human-owned
step, so it is the owner's: the ticket is at a `human-owns-and-finishes` step
and an agent should not bump it.

Related: the same task directory carries
`narrative-candidates.md`, which is the subject of the separate ticket
`narrative-candidates-md-publishes-log-text-the-own` — a confidentiality
exposure that should be settled **before** anything closes or archives this task
directory.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
