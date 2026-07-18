---
slug: recurring-bugs/recurring-scan-should-skip-and-report-an-unloadabl
title: recurring scan should skip-and-report an unloadable template, not crash the
  repo
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

During `coga recurring --all ~/Code` (2026-07-17), the `demo-recall` repo
crashed the entire scan with a non-zero (exit 1) traceback instead of
skipping the offending template:

```
ValueError: Workflow 'megalaunch/run' references missing skills:
['coga/megalaunch/run']
  File ".../recurring.py", line 306, in scan_due
    outcome = create_template(...)
  File ".../recurring.py", line 429, in create_template
    outcome = _create_at_slug(...)
  File ".../recurring.py", line 637, in _create_at_slug
    ref = create_task(...)
  File ".../create.py", line 95, in create_task
    raise ValueError("Workflow ... references missing skills ...")
```

A single template whose frozen workflow references a missing skill takes the
whole repo's recurring scan down. The recurring design already says an
unloadable template should **skip-and-report** (the scan table prints an
error row and continues), the same way `coga recurring list` renders a
failing template as an error row rather than crashing the view.

**Fix direction:** wrap the per-template `create_template` /
`create_task` call in `scan_due` (`recurring.py:306`) so a template that
fails to instantiate (missing skill, bad workflow, schema error) is reported
as a skipped/error row and the loop moves to the next template, rather than
propagating the exception out of the scan. Keep it fail-loud in the report
(the error must be visible), just not fatal to sibling templates.

## Context

- Crash site: `src/coga/recurring.py` `scan_due` → `create_template` →
  `_create_at_slug` → `src/coga/create.py:95` (`create_task`).
- Compare the already-tolerant path: `coga recurring list` renders a
  load-failing template as an error row (see `recurring_runner`/`recurring`
  list rendering).
- The `demo-recall` repo itself has a stale `megalaunch/run` template that
  references a skill `coga/megalaunch/run` that no longer exists — that repo
  needs its own cleanup, but that is not this ticket; this ticket is the
  engine robustness so one bad template can't starve the rest of the sweep.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
