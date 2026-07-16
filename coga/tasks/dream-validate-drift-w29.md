---
slug: dream-validate-drift-w29
title: Dream validate-drift W29
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dream/validate-drift
  steps:
  - name: run
    skills:
    - bootstrap/dream/tasks/validate-drift
    assignee: agent
secrets: null
script: null
---

## Description



## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dream Skill: validate-drift

Generated: 2026-07-16T03:36:09+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `dream-validate-drift-w29`

Result: 31 issue(s): 0 direct fix, 0 PR proposal, 31 human-needed.

### Human Needed

- `cleanup-core-commands/launch-decomposition`: `stuck-in-progress` (warn) - in_progress but idle for 149.5h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `cleanup-core-commands/lifecycle-verbs-to-ticket-operations`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `cleanup-core-commands/read-report-commands-as-ticket-workflows`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `cleanup-core-commands/residual-command-surfaces`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `cleanup-core-commands/support-commands-boundary`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `cleanup-core-commands/work-orchestration-commands-to-tickets`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `handle-better-delete-branches-autcommit`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `handle-better-delete-branches-autcommit`: `unsynthesized-draft-blackboard` (warn) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review, ## Proposals); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `improve-prompt-for-relay-ticket`: `stuck-in-progress` (warn) - in_progress but idle for 479.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `move-open-pr-gate-from-launch-into-bump-make-open`: `stuck-in-progress` (warn) - in_progress but idle for 237.5h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `move-open-pr-recipe-into-the-code-open-pr-skill-ke`: `unsynthesized-draft-blackboard` (warn) - draft blackboard has pre-launch authoring notes (non-placeholder blackboard is 2389 characters); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `nightly-auto-drain-run-for-ready-tickets`: `stuck-in-progress` (warn) - in_progress but idle for 308.8h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `remove-mode-from-ticket-frontmatter-and-deduce-scr`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `resolve-blocker-inline-via-chat-on-interactive-lau`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `stop-direct-body-tickets-from-stranding-committed`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `stop-trimming-blackboard-but-refuse-to-launch-befo`: `stuck-in-progress` (warn) - in_progress but idle for 334.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `ticket-must-merge-blackblaord`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `v2/acceptance-criteria`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/autotrigger-ticket-type`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/autotrigger-ticket-type`: `unsynthesized-draft-blackboard` (warn) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `v2/clean-uncommitted-work`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/identify-blocking-issues`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/issue-inbox-slack`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/measure-relay-prompt-scope-and-agent-precision`: `unsynthesized-draft-blackboard` (warn) - draft blackboard has pre-launch authoring notes (non-placeholder blackboard is 4213 characters); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `v2/relay-design-repositories`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/split-context-to-doc-user-accessible-and-editable`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/split-context-to-doc-user-accessible-and-editable`: `unsynthesized-draft-blackboard` (warn) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `v2/use-worktree-when-starting-a-dev-task`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/use-worktree-when-starting-a-dev-task`: `unsynthesized-draft-blackboard` (warn) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `warn-on-launch-when-the-installed-coga-predates-th`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `write-real-coga-documentation-command-reference-gu`: `stuck-in-progress` (warn) - in_progress but idle for 247.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
