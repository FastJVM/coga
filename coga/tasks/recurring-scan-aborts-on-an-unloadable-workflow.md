---
title: A recurring template whose workflow does not load aborts the whole scan
status: canceled
owner: nicktoper
workflow: null
---

## Description

`scan_due` is meant to skip a bad template and report it, but a template whose
`workflow:` does not load raises `WorkflowError` straight out of `create_task`,
which `_create_at_slug` does not convert to `RecurringError` — so `coga
recurring` dies with a traceback and no template after it in sort order is
scanned. Convert `WorkflowError` there too, so the template lands in
`scan.errors` like any other bad template.

## Context

**Seen 2026-09-14 in FastJVM/admin**, on coga `f56899fc` (then `origin/main`).
#786 removed the `digest/post` workflow, but admin still carried its local
`coga/recurring/digest/` template declaring `workflow: digest/post`. Every bare
`coga recurring` then crashed:

```
recurring.py  scan_due          -> create_template(...)
recurring.py  create_template   -> _create_at_slug(...)
recurring.py  _create_at_slug   -> create_task(...)
create.py:100 create_task       -> Workflow.load(resolve_workflow_path(cfg, workflow_name))
workflow.py:64 Workflow.load
WorkflowError: Workflow not found: /home/zach2179/dev/admin/coga/workflows/digest/post.md
```

**Why it is worse than one broken template.** Templates are scanned in
`sorted(root.iterdir())` order in `scan_due`, so the escape starves every
template after the bad one — in admin, 17 of 27, including `dream`,
`repo-guards` and `skill-update`. Nothing is created, so the period is never
serviced, and every later run crashes the same way. Admin has since deleted
its orphan, so it no longer reproduces there; the defect is the escape, and a
typo in `workflow:` or the next workflow removed upstream hits it identically.

**Where.** The `except (TaskValidationError, ValueError)` right after the
`create_task` call in `_create_at_slug` (`src/coga/recurring.py`). Its own
comment says both "must become RecurringError so scan_due skips and reports
this template instead of aborting the whole sweep" — `WorkflowError` is the
case it misses. `create_task` raises it at `create.py:100`, before anything is
written, so there is nothing to roll back.

**Precedent in the same file.** The delegation check in `create_template` and
`_validate_promoted_workflow` both already wrap `Workflow.load` and re-raise
`WorkflowError` as `RecurringError`. Only the non-delegating create path
does not.

**Fix:** add `WorkflowError` to that `except` tuple. Regression test beside
`test_scan_due_skips_bad_template` (`tests/test_recurring.py`): a template
declaring `workflow: nope/missing` next to a good one — assert the good one is
still created and `scan.errors` names the bad one. Seen only through the bare
interactive `coga recurring`; whether the unattended runner catches it higher
up was not checked.

<!-- coga:blackboard -->
