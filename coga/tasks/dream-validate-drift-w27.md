---
slug: dream-validate-drift-w27
title: Dream validate-drift (W27)
status: done
mode: script
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

Generated: 2026-06-30T05:41:03+00:00
Command: `/home/n/.local/share/pipx/venvs/coga/bin/python -m coga.validate --json --fix`
Task: `dream-validate-drift-w27`

Applied fixes: 10.

- `install/README`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/README.md`)
- `install/document-where-to-run-init-and-adopt-existing-repo`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/document-where-to-run-init-and-adopt-existing-repo/ticket.md`)
- `install/external-users-cannot-install-managed-skills`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/external-users-cannot-install-managed-skills/ticket.md`)
- `install/harden-packaging-and-install-before-launch`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/harden-packaging-and-install-before-launch/ticket.md`)
- `install/init-does-not-persist-user-then-blocks-on-reinit`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/init-does-not-persist-user-then-blocks-on-reinit/ticket.md`)
- `install/pip-hash-requirement-breaks-editable-install`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/pip-hash-requirement-breaks-editable-install/ticket.md`)
- `install/recommend-virtualenv-not-system-python`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/recommend-virtualenv-not-system-python/ticket.md`)
- `install/relay-help-and-cli-should-not-require-user`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/relay-help-and-cli-should-not-require-user/ticket.md`)
- `install/retest-ssh-https-and-init-reclone-on-fresh-machine`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/install/retest-ssh-https-and-init-reclone-on-fresh-machine/ticket.md`)
- `marketing/README`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/marketing/README.md`)

Result: 44 issue(s): 0 direct fix, 0 PR proposal, 44 human-needed.

### Human Needed

- `drain-pending-auto-tickets-with-leftover-session-b`: `stuck-in-progress` (warn) - in_progress but idle for 129.9h
  Remediation: Ask the owner whether the task should be relaunched, panicked, paused, or bumped. The skill should not change lifecycle state silently.
- `filter-relay-status-by-directory-group`: `stuck-in-progress` (warn) - in_progress but idle for 73.9h
  Remediation: Ask the owner whether the task should be relaunched, panicked, paused, or bumped. The skill should not change lifecycle state silently.
- `handle-better-delete-branches-autcommit`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `improve-prompt-for-relay-ticket`: `stuck-in-progress` (warn) - in_progress but idle for 97.2h
  Remediation: Ask the owner whether the task should be relaunched, panicked, paused, or bumped. The skill should not change lifecycle state silently.
- `install/README`: `bad-frontmatter` (error) - ticket.md must begin with YAML frontmatter between --- lines
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/document-where-to-run-init-and-adopt-existing-repo`: `missing-key` (error) - frontmatter missing required key 'slug'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/document-where-to-run-init-and-adopt-existing-repo`: `missing-key` (error) - frontmatter missing required key 'autonomy'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/document-where-to-run-init-and-adopt-existing-repo`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/external-users-cannot-install-managed-skills`: `missing-key` (error) - frontmatter missing required key 'slug'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/external-users-cannot-install-managed-skills`: `missing-key` (error) - frontmatter missing required key 'autonomy'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/external-users-cannot-install-managed-skills`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/harden-packaging-and-install-before-launch`: `missing-key` (error) - frontmatter missing required key 'slug'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/harden-packaging-and-install-before-launch`: `missing-key` (error) - frontmatter missing required key 'autonomy'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/harden-packaging-and-install-before-launch`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/init-does-not-persist-user-then-blocks-on-reinit`: `missing-key` (error) - frontmatter missing required key 'slug'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/init-does-not-persist-user-then-blocks-on-reinit`: `missing-key` (error) - frontmatter missing required key 'autonomy'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/init-does-not-persist-user-then-blocks-on-reinit`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/pip-hash-requirement-breaks-editable-install`: `missing-key` (error) - frontmatter missing required key 'slug'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/pip-hash-requirement-breaks-editable-install`: `missing-key` (error) - frontmatter missing required key 'autonomy'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/pip-hash-requirement-breaks-editable-install`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/recommend-virtualenv-not-system-python`: `missing-key` (error) - frontmatter missing required key 'slug'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/recommend-virtualenv-not-system-python`: `missing-key` (error) - frontmatter missing required key 'autonomy'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/recommend-virtualenv-not-system-python`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/relay-help-and-cli-should-not-require-user`: `missing-key` (error) - frontmatter missing required key 'slug'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/relay-help-and-cli-should-not-require-user`: `missing-key` (error) - frontmatter missing required key 'autonomy'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/relay-help-and-cli-should-not-require-user`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/retest-ssh-https-and-init-reclone-on-fresh-machine`: `missing-key` (error) - frontmatter missing required key 'slug'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/retest-ssh-https-and-init-reclone-on-fresh-machine`: `missing-key` (error) - frontmatter missing required key 'autonomy'
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `install/retest-ssh-https-and-init-reclone-on-fresh-machine`: `orphan-extension` (warn) - frontmatter key 'mode' is not in the canonical schema and is not declared in `[ticket.fields]` — likely orphaned by a removed declaration; delete it from this ticket or restore the `[ticket.fields]` entry
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `marketing/README`: `bad-frontmatter` (error) - ticket.md must begin with YAML frontmatter between --- lines
  Remediation: Ticket frontmatter shape is the source of truth. Ask the owner to repair the file rather than synthesizing values from inference.
- `marketing/auto-width-200`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `marketing/relay-discord`: `unknown-assignee` (warn) - assignee 'nick' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field`: `stuck-in-progress` (warn) - in_progress but idle for 73.9h
  Remediation: Ask the owner whether the task should be relaunched, panicked, paused, or bumped. The skill should not change lifecycle state silently.
- `nightly-auto-drain-run-for-ready-tickets`: `stuck-in-progress` (warn) - in_progress but idle for 110.9h
  Remediation: Ask the owner whether the task should be relaunched, panicked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/acceptance-criteria`: `unknown-assignee` (warn) - assignee 'nick' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/add-dev-testing-setup-skill`: `stuck-in-progress` (warn) - in_progress but idle for 463.0h
  Remediation: Ask the owner whether the task should be relaunched, panicked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/autotrigger-ticket-type`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/clean-uncommitted-work`: `unknown-assignee` (warn) - assignee 'nick' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/identify-blocking-issues`: `unknown-assignee` (warn) - assignee 'nick' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/issue-inbox-slack`: `unknown-assignee` (warn) - assignee 'nick' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/relay-design-repositories`: `unknown-assignee` (warn) - assignee 'nick' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/split-context-to-doc-user-accessible-and-editable`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/use-worktree-when-starting-a-dev-task`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `wire-autonomy-triage-into-impl-ready-workflows`: `stuck-in-progress` (warn) - in_progress but idle for 336.7h
  Remediation: Ask the owner whether the task should be relaunched, panicked, paused, or bumped. The skill should not change lifecycle state silently.
