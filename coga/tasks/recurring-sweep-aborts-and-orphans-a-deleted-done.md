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
step: 3 (open-pr)
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

Implementation initially committed as `f3e705d1`; final peer-review rebase and
verification are recorded below. No feature-branch push in this step.

## Peer review

- `codex review --base main` **returned**, exit 0, with no actionable
  findings. It ran recurring + packaging checks (364 passed) and creation +
  validation checks (188 passed), using the primary checkout's venv and the
  feature source. No review fix or design change was needed.
- A temporary combined probe drove the real scan, report rendering, and
  autofix record writer, with child execution and the analyst stubbed and
  notifications suppressed. A missing workflow left the stale done ticket
  byte-identical, preserved its attachment and prior serviced period, yielded
  exactly one scan error, and allowed the later template to complete. The
  saved run record reached the analyst with the workflow error present.
  Command: `PYTHONPATH=/home/n/Code/claude/coga-recurring-missing-workflow/src:/home/n/Code/claude/coga-recurring-missing-workflow/tests /home/n/Code/claude/coga/.venv/bin/python /tmp/coga-recurring-missing-workflow-smoke.py`.
- No raw-terminal loop, pager, interactive prompt, or rendered Slack surface
  changed. The new stderr diagnostic is covered by the regression test; the
  combined probe also confirmed the visible scan error and continuation.
- Required `git fetch origin main && git rebase FETCH_HEAD` completed without
  conflicts onto `ef2c02d5`; feature commit is now `e62d818f`.
  `git range-diff f3e705d1^..f3e705d1 e62d818f^..e62d818f` confirms the reviewed
  patch is unchanged, and `git diff --check main...HEAD` passed.
- `PYTHONPATH=/home/n/Code/claude/coga-recurring-missing-workflow/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --task recurring-sweep-aborts-and-orphans-a-deleted-done --json`
  passed: one valid task, no errors, expected `missing-user` warning in the
  feature worktree without machine-local configuration.
- Full suite after rebase: `PYTHONPATH=/home/n/Code/claude/coga-recurring-missing-workflow/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  **2499 passed in 181.89s**, exit 0. Output:
  `/tmp/coga-recurring-missing-workflow-peer-full.log`.
- Primary-checkout validation also passed with one valid task and no issues:
  `PYTHONPATH=/home/n/Code/claude/coga/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --task recurring-sweep-aborts-and-orphans-a-deleted-done --json`.
- The feature branch is clean and retains its implementation commit. Commits
  landing on `main` during verification change only task/log state; no source
  or context drift was introduced after the rebase. No findings remain open.

## PR

Recurring sweeps could delete a stale completed period task and then abort when
its template referenced a removed workflow, leaving earlier creations unsynced
and later templates unprocessed. Resolve the replacement workflow and all step
skills before deletion, and report workflow-loading failures as per-template
scan errors so the remaining sweep and autofix reporting can finish.

Also report control-fetch failures on stderr and in the task log before the
existing sync fallback. Add regressions for missing workflows, missing step
skills, fresh creation, and fetch-failure reporting; update the recurring
contract and its packaged twin.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-recurring-missing-workflow/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` — 2499 passed after rebase; scoped task validation passed; combined scan-to-autofix probe passed with child execution and analysis stubbed.
