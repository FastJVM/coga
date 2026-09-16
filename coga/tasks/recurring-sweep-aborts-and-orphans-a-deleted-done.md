---
title: Recurring sweep aborts and orphans a deleted done period task when a template's
  workflow is missing
status: in_progress
owner: nicktoper
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
step: 1 (implement)
agent: claude
---

## Description

`recurring.get_or_create` replaces a stale `done` period task by calling `run_delete_task` and then `_create_at_slug`. `_create_at_slug` (`src/coga/recurring.py`, the `except (TaskValidationError, ValueError)` clause) only converts those two exception types into the per-template `RecurringError` that `scan_due` catches, so a `WorkflowError` from `create_task` — e.g. `Workflow not found: coga/workflows/digest/post.md` after #786 removed the digest workflow while a repo still carried a `recurring/digest/` template — escapes and aborts the whole sweep.

Observed in the multiply repo on 2026-09-14 (`coga recurring --all ~/Code`): the three templates sorted before `digest` were deleted and recreated locally, then the sweep died at `digest` before `_sync_recurring_create` ran. Consequences: (1) the recreated `active` tickets were never landed by the create-sync, so every later end-of-command `sync_coga_state` sweep refused them as `done → active` regressions and, because a refusal aborts the whole sweep, also held back an unrelated ticket's step handoff; (2) the stale `done` digest task was deleted with no `deleted completed prior-period task` log line (that line is appended only after create); (3) later templates (`dream`, `skill-update`) never ran and no run record was written.

### Acceptance criteria

- A template whose `workflow:` (or step skill) does not resolve is reported as a per-template scan error and skipped; the rest of the sweep runs, the run record is written, and the autofix loop still sees it.
- The stale `done` task is not deleted unless the replacement can be created: resolve/validate the template's workflow before `run_delete_task`, or make delete-then-create atomic.
- The `_fetch_control_branch` fallback in `_sync_recurring_create_paths` records the swallowed fetch error (stderr + log line) instead of falling through silently.
- Regression test: a template pointing at a missing workflow, with a stale done period task on disk, leaves that task in place, produces one scan error, and does not stop later templates.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
