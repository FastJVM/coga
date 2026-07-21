---
slug: add-a-status-canceled-for-ticket
title: add a status canceled for ticket
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Add `canceled` as a first-class terminal ticket status in Coga's control
plane. This lets operators close Dream findings and other tickets that were
intentionally declined without misrepresenting them as completed work. Expose
the transition as `coga mark canceled <ticket> --message "<reason>"` and require
a non-empty reason so the decision remains legible in the audit trail.

## Context

`canceled` is terminal: it has no transition back to `active`, and canceling a
ticket clears its current workflow step. The command should accept every
non-terminal ticket state, including `draft`, because unpursued Dream findings
are commonly canceled before activation. Like `done`, canceled tickets are
hidden from the default `coga status` view and included by `--all`; status
totals and help text should represent that behavior clearly.

Treat cancellation as a complete control-plane lifecycle addition rather than
only a validator enum change. Update the shared transition implementation, CLI,
validation and terminal-state invariants, launched-session termination,
read/status views, branch cleanup eligibility, notifications/audit logging,
tests, and user-facing behavioral documentation. Keep the live repo contexts
and packaged template copies synchronized where the contract changes. Do not
add a reopen path or silently reinterpret `canceled` as `done`; completion and
intentional abandonment must remain distinguishable.

Cover cancellation from `blocked` explicitly: existing blocker text remains
historical blackboard content, while the ticket becomes terminal and its
workflow step is cleared. Enforce terminal behavior consistently by rejecting
launch, bump, reactivation, autoclose, and other mutations that require a
non-terminal ticket. Persist the required cancellation reason in the
append-only audit log; it does not need a second canonical copy in the ticket
blackboard or `coga show`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
