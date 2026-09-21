---
title: 'validate-drift: empty-description — 23 title-only tickets need an author verdict'
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

validate-drift: empty-description

Filed by Dream 2026-W39, Phase 6 (validate-drift disposition). `coga validate --json` is the live member list for this class; membership below is this run's snapshot and is not copied run to run. This ticket is the durable record that the class needs a human decision. Dream does not change lifecycle, workflow, or assignee state.

**Completion rule.** This ticket stays open until the class is empty or the decision is recorded in a context. Before closing it with accepted warnings remaining, preserve the same tag line, the decision, its rationale, and the scope (conditions or members it covers) in the appropriate context, so the decision survives this ticket's retirement and later Dream runs can apply it instead of refiling.

**Class.** 23 title-only tickets (empty `## Description`): 17 under `coga/tasks/v2/`, 6 at the root or under `marketing/`. Recipe remediation: "A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one."

**Recorded but unowned decision.** The previous owner of the v2 half, `interview-the-owner-on-the-17-title-only-v2-stubs`, was canceled at `review-design` on 2026-09-20 with the owner's reasoning on its blackboard: per-stub cancels are wasted motion because `coga/tasks/v2/` is to be parked somewhere `coga status` does not reach, and that follow-up is "not yet a ticket". Its verdict table (17 cancels, 0 describes, incl. `pick-model-on-workflow-to-save-on-cost`) and the migration inventory (which contexts, commands, and tests assume `v2/` is live) are on that canceled ticket. That decision lives only on a canceled ticket's blackboard — no context carries it, so this class has no recorded disposition yet. Dream 2026-W39 also opened a proposal PR recording the parking decision in `coga/roadmap` (extract finding F1, PR #863); if it merges, the v2 members are covered by that context once the tag line is preserved there.

**Decision needed.** (a) The 6 non-v2 stubs need the author's describe-or-cancel verdict now — they read as current work in `coga status`; (b) confirm whether the v2 stubs are waived until the "park v2 off the status path" ticket exists, and record that scope in a context with this tag line.

**Members this run (2026-09-21):**
- `dream-should-be-able-to-use-codex-instead-of-claud` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `invert-command-line-to-have-actions-passed-last-or` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `marketing/fix-installer` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `some-recurring-tasks-are-not-launched-correctly-to` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `stop-recurring-on-inactive-repo` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/add-subproject` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/autoroute-agent-based-on-remaining-usage` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/create-vault-and-service-account-for-mid-trust-sec` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/create-vault6-and-service-account-for-high-trust-s` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/docs-and-contt-block-should-be-merged` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/generic-lib-to-use-e-g-patent-models` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/in-general-relay-files-should-be-easier-to-access` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/manage-security-and-pii` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/model-selector` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/pick-model-on-workflow-to-save-on-cost` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/project-manager-split-spec-in-tickets-block` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/remote-stale-command-line-toosl` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/script-mode-to-activate` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/simplify-command-lines` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/sync-support-files-and-bare-ticket-authoring` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/update-all-doesn-t-copy-workflow-correctly-to-atta` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `v2/why-ai-asks-me-to-bump-instead-of-doing-it` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
- `where-have-code-review-disappeared` — `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
