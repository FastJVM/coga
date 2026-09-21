---
title: 'validate-drift: stuck-in-progress — 11 in_progress tickets idle past threshold
  need an owner verdict'
status: draft
owner: nicktoper
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
step: 1 (brief-and-hand-off)
---

## Description

validate-drift: stuck-in-progress

Filed by Dream 2026-W39, Phase 6 (validate-drift disposition). `coga validate --json` is the live member list for this class; membership below is this run's snapshot and is not copied run to run. This ticket is the durable record that the class needs a human decision. Dream does not change lifecycle, workflow, or assignee state.

**Completion rule.** This ticket stays open until the class is empty or the decision is recorded in a context. Before closing it with accepted warnings remaining, preserve the same tag line, the decision, its rationale, and the scope (conditions or members it covers) in the appropriate context, so the decision survives this ticket's retirement and later Dream runs can apply it instead of refiling.

**Class.** 11 tickets are `in_progress` but idle past the validator's threshold. Recipe remediation: "Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently."

**Decision needed.** For each member: relaunch, block with a reason, pause, bump, or cancel — or record in a context which idle shapes are accepted (e.g. review-step tickets waiting on the owner's PR review) so the validator warning is a known baseline for that scope.

**Members this run (2026-09-21):**
- `add-an-agent-picker-for-recurring` — in_progress but idle for 253.6h
- `adjudicate-the-eight-premise-dead-v2-drafts` — in_progress but idle for 91.8h
- `cleanup/publish-coga-1-0-to-pypi` — in_progress but idle for 136.2h
- `define-the-api-equivalent-cost-proxy-and-price-tab` — in_progress but idle for 145.4h
- `define-the-split-a-ticket-mechanic-shared-by-code` — in_progress but idle for 108.9h
- `marketing/build-the-launch-plan` — in_progress but idle for 406.5h
- `marketing/phase-0-audit` — in_progress but idle for 263.5h
- `phase-0-audit-is-complete-per-the-plan-but-still-i` — in_progress but idle for 117.4h
- `recurring-sweep-wedges-on-the-ticket-py-it-copies` — in_progress but idle for 265.1h
- `redo-documentation-dir-and-merge-it-with-context-b` — in_progress but idle for 303.8h
- `v2/document-contexts-as-prompt-payload-not-tags-princ` — in_progress but idle for 1485.2h

Related but not an owner of the class: `phase-0-audit-is-complete-per-the-plan-but-still-i` (itself a member) covers only `marketing/phase-0-audit`. Several members sit at a `review` step with an open PR (see `gh pr list`), which is probably the accepted shape to record.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
