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
step: 2 (peer-review)
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

## Dev

branch: recurring-missing-workflow
worktree: /home/n/Code/claude/coga-recurring-missing-workflow

Separate feature checkout (linked worktree). Tests run there with the primary
checkout's venv: `/home/n/Code/claude/coga/.venv/bin/python -m pytest`
(pyproject's `pythonpath = ["src"]` picks up the worktree source).

## Findings

- Root cause, confirmed: `create.create_task` raises `WorkflowError` from
  `Workflow.load(resolve_workflow_path(...))`; `recurring._create_at_slug`
  only caught `TaskValidationError`/`ValueError`, so it escaped `scan_due`.
  A missing *step skill* was already a `ValueError` (caught) — but on the
  replace-done path `run_delete_task` had already run, so the stale task
  was gone either way.
- The `_fetch_control_branch` fallback in
  `recurring_runner._sync_recurring_create_paths` caught `git.GitError`
  bare and fell through to `git.sync_paths` with no stderr/log note.

## Decisions

- Gate, don't transact: new `recurring.assert_template_workflow(cfg,
  template)` (loads the workflow, checks every step skill via
  `resolve_skill_path`) runs in `create_template` before `run_delete_task`.
  Duplicates a check `create_task` does a moment later; chosen over making
  delete+create atomic because it needs no rollback machinery.
- `_create_at_slug` also converts `WorkflowError` → `RecurringError`, so the
  fresh-create path degrades to a per-template error too.
- Fallback reporting reuses the existing `_append_sync_failure` helper
  (`sync failed: <exc>` log line) plus a distinct stderr line
  `[git] control fetch failed (landing locally only): ...`, so it does not
  masquerade as the later `sync_paths` failure line.
- Context: added the precondition to `coga/contexts/coga/recurring/SKILL.md`
  ("The scheduler is the liveness fallback" paragraph) and its packaged twin.

## Tests (tests/test_recurring.py)

- `test_scan_due_keeps_stale_done_task_when_template_workflow_is_missing`
- `test_scan_due_keeps_stale_done_task_when_step_skill_is_missing`
- `test_scan_due_reports_missing_workflow_on_fresh_create`
- `test_recurring_create_sync_reports_control_fetch_failure_before_fallback`
All four verified failing before the fix. Full suite: 2499 passed.

## Acceptance mapping

- Per-template error + rest of sweep runs: scan errors already feed the run
  record and autofix loop (unchanged path); regression tests cover the scan.
- Stale done task not deleted unless replacement creatable: gate above.
- Fetch fallback records the error: stderr + log line.
- Regression test: first test above.

Commit `f3e705d1` on the branch; rebased on current `origin/main`; no push.

## Peer review

- `codex review --base main` is running in the recorded feature worktree;
  its final assessment has not returned yet. Do not advance on this note.
- Reviewer checks so far: recurring + packaging, 364 passed; creation +
  validation, 188 passed. The final full-suite run will use the primary venv
  with absolute `PYTHONPATH` pointing at the feature worktree's `src`.
- Manual trace confirms scan errors flow into `RunRecord.scan_errors`, and
  `run_autofix` writes that record before invoking the analyst. A combined
  local probe, fresh rebase, full suite, and final review outcome remain.
