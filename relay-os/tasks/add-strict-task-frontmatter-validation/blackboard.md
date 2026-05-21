The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design Notes

- Human asked to design the ticket first before implementation.
- Core target: strict validation for a whole task directory, not only YAML parse.
- Required task files: `ticket.md`, `blackboard.md`, `log.md`.
- Required canonical task frontmatter after the change:
  `title`, `status`, `mode`, `owner`, `human`, `agent`, `assignee`,
  `contexts`, `skills`, `workflow`.
- `contexts: []`, `skills: []`, and `workflow: null` are mandatory even when
  empty.
- Human explicitly corrected the field name to `skills:` plural.
- Proposed model: `skills:` is ticket-level process knowledge; workflow is
  optional and workflow steps may also carry step-local `skills:`.
- The ticket's own workflow frontmatter still uses legacy singular `skill:`
  so current Relay can launch it before the migration lands.
- Enforcement should live in `relay validate` and post-edit CLI hooks; a skill
  can document the habit but cannot reliably intercept every edit.

## Local Notes

- `relay create "Add strict task frontmatter validation"` created the draft
  task locally.
- The create Slack broadcast failed because this sandbox could not resolve
  `hooks.slack.com`; the failure was appended to `log.md` by the CLI.

## Dev

branch: add-strict-task-validation
worktree: /home/n/Code/relay-strict-validate
pr: https://github.com/FastJVM/relay/pull/156

## Implementation Notes

Scope:
1. `WorkflowStep.skill: str | None` → `WorkflowStep.skills: list[str]`;
   `Workflow.freeze()` emits `skills:` list; `Workflow.load` rejects singular
   `skill:` at parse time. Compose layer iterates step skills.
2. `Ticket.skill` removed; `Ticket.skills` (list) added. Top-level skill
   composition uses the new list.
3. `scaffold_task` always emits canonical frontmatter with `contexts: []`,
   `skills: []`, `workflow: null` when empty. Accepts `skills:` list, drops
   the singular `skill:` arg (callers updated).
4. `validate.py`:
   - Strict canonical task schema check.
   - `validate_ticket_frontmatter(cfg, task_label, ticket)` returns issues.
   - `validate_task_dir(cfg, ref)` returns issues (files + frontmatter).
   - `validate_task(cfg, slug)` returns a single-task `Report`.
5. `relay validate --task <slug>` CLI flag.
6. Post-edit hook calls in all write paths: scaffold, mark, bump, launch
   start, retire, recurring, ticket-authoring exit. Hard exit on errors.
7. Migrate workflow fixtures, bootstrap shims, all shipped tasks, resource
   templates, example fixture, and tests.

This ticket's own `workflow:` step in frontmatter must be migrated too
(currently still `skill: code/implement-and-pr`) — after the implementation
lands, otherwise the in-flight launcher refuses it. Migrate as part of
the global pass.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: Document relay validate --task and the launch freshness check in relay/cli
