---
slug: add-a-status-canceled-for-ticket
title: add a status canceled for ticket
status: draft
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
  - dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Ticket authoring notes

- Human confirmed command shape: `coga mark canceled <ticket>`.
- Human confirmed canceled tickets are hidden by default and need no reopen path.
- Human confirmed cancellation must require a reason.
- Proposed autonomy tier: human-verify. The code change is conventional and
  testable, but lifecycle semantics have broad control-plane impact; the chosen
  code workflow includes peer review and an owner gate.

## Evaluator review

The ticket is clear and implementation-ready: it defines the new status, command syntax, required reason, allowed source states, terminal behavior, status visibility, and the major integration surfaces. `code/with-review` fits the broad control-plane change and its human review gate; `dev/code` is relevant and appropriately narrow. No additional broad context should be attached—the ticket already states the necessary lifecycle contract, while repository guidance directs the implementer to the canonical architecture and packaged/live copies.

The scope is sizable but cohesive as one lifecycle feature rather than multiple independent tickets. Two edge cases merit explicit decisions or test coverage during implementation: canceling a `blocked` ticket should clarify whether blocker text remains as historical blackboard content, and “terminal” should consistently make `canceled` ineligible for launch, bump, reactivation, autoclose, and other done-only mutations. The required cancellation reason should also have a defined durable representation: the ticket currently guarantees audit-trail legibility, but does not say whether it must additionally remain visible in the ticket blackboard or `coga show`.
