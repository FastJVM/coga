---
title: 'validate-drift: stuck-in-progress — 11 in_progress tickets idle past threshold
  need an owner verdict'
status: in_progress
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
step: 2 (human-executes)
agent: claude
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

## Brief for owner (agent, 2026-10-07, read-only)

**Goal.** Empty the `stuck-in-progress` validator class, or record in a
context which idle shapes are an accepted baseline, so Dream stops refiling.

**Live membership has changed.** `coga validate --json` today lists **7**
members, not the 11 in the 2026-09-21 snapshot. Only
`marketing/build-the-launch-plan` carried over; the other 10 have left the
class. Current members, by shape:

| Member | Step | Shape |
|---|---|---|
| `gigantic-refactor-move-recurring-recipes-out-of-co` | 3 review-design | owner design-review gate, no PR (172.8h) |
| `launch-locks/ticket-ownership-lock` | 3 review-design | owner must disposition 6 must-fix findings (144.3h) |
| `lifecycle-writes-read-control-s-ticket-before-modi` | 3 review-design | owner design-review gate (219.6h) |
| `run-recurring-agent-templates-off-the-control-bran` | 3 review-design | open question on blackboard: follow-up ticket, retarget, or leave it (118.5h) |
| `carry-the-apply-the-register-amendment-step-in-a-w` | 2 human-owns-and-finishes | owner-held draft-for-human step (173.7h) |
| `marketing/build-the-launch-plan` | 2 human-owns-and-finishes | owner-held V1 launch execution (292.9h) |
| `add-an-applying-a-batch-of-verdicts-section-to-the` | 4 review | **its PR #912 is CLOSED (not merged)**, so it is not waiting on a live review (217.5h) |

The ticket's hunch ("review step with an open PR") does not fit any current
member: none of them has an open PR. All 7 sit at an **owner-assigned step**.
No context records a stuck-in-progress baseline yet. A grep of
`docs/contexts` for `stuck-in-progress` found nothing.

**Ordered steps for the owner.**
1. `add-an-applying-a-batch-of-verdicts-section-to-the`: decide why #912
   was closed. Then either reopen or re-raise the PR, or `coga mark canceled`.
   This is the only member that looks actually orphaned.
2. For each of the 4 `review-design` tickets, review the design on the
   blackboard and then `coga bump`, send it back with feedback, or cancel.
   The ownership lock needs its 6 must-fix findings dispositioned. The recurring
   refusal ticket needs the follow-up/retarget/leave answer.
3. For the 2 `human-owns-and-finishes` tickets, finish and `coga mark done`
   them, or `coga mark canceled` them, or leave them if they really are
   long-running.
4. Optional: record a baseline. If owner-held steps (`assignee: owner`) idle
   past the threshold are acceptable, add a short entry with the tag line
   `validate-drift: stuck-in-progress`, the decision, the rationale, and the
   scope (for example "in_progress at an owner-assignee step; agent-assignee
   steps are never accepted"). Put it in the topic that owns validate-drift
   dispositions, likely `docs/contexts/coga/dream/SKILL.md` or the lifecycle
   topic. Same-PR rules apply.

**Irreversible action.** `coga mark canceled` on any member, and pushing or
merging a PR, are not easily undone. Bumps are forward-only for agents. Context
edits go through a normal PR.

**Done check (for verify-read-only).** `coga validate --json` shows no
`stuck-in-progress` entries, or every remaining entry falls within a scope
written down in a context under the tag line above.
