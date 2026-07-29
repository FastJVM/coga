---
slug: scrub-coga-task-in-the-pytest-autouse-guard-so-fix
title: Scrub COGA_TASK_* in the pytest autouse guard so fixture reports cannot reach
  live tickets
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

Filed by the Dream run of 2026-W31 (Phase 2 knowledge scan, finding F13, class
`gap`).

## The symptom

Twenty-plus `## Dream Skill: validate-drift` sections are appended across four
live ticket blackboards — `make-sure-we-can-drop-new-recurring-tickets` (x9),
`install/short-notice-instead-of-raw-git-error-when-sync-ha` (x4),
`agree-the-core-vs-skills-move-list-then-execute` (x2), and
`ship-a-shared-recurring-reminder-engine-battery` (x3). Every one of them reports:

```
`x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)
committed and pushed `repair-branch`
```

None of that is real. There is no task `x`. Coga has no per-task `log.md`
(`validate.py:361` says so explicitly). And `coga validate --fix` classifies
`missing-file` as `human-needed` and creates nothing.

## The cause

That text is verbatim **test-fixture data** from
`tests/test_dream_validate_drift.py:341-352` and `:322`. A `pytest` run started
from inside a `coga launch` session inherits `COGA_TASK_BLACKBOARD`, and the
recipe under test appends its fixture report to the live **outer** ticket.

`coga/contexts/coga/codebase/SKILL.md` already documents this hazard and
prescribes the remedy — "Clear every launch-owned metadata variable in the
autouse environment guard." But `tests/conftest.py::_clear_supervised_session_env`
clears only `COGA_DONE_SENTINEL`, `COGA_SUPERVISED`, `COGA_EXPECTED_TASK`, and
`COGA_EXPECTED_STEP`. The whole `COGA_TASK_*` family is absent, and only 2 of the
10 tests in that module opt out with a per-test `monkeypatch.delenv` — exactly the
"remember to do it" pattern the context warns against.

So the knowledge exists; the enforcement does not. That is why this is a code
ticket rather than a context edit.

## Scope

1. Add the full launch-owned set to the autouse guard: `COGA_TASK_SLUG`,
   `COGA_TASK_DIR`, `COGA_TASK_TICKET`, `COGA_TASK_BLACKBOARD`, `COGA_TASK_LOG`,
   `COGA_COGA_OS_ROOT`, `COGA_REPO_ROOT`, and the `COGA_SKILL_*` pair. Prefer
   deriving the list from `task_env.py` over hand-listing it, so a new variable
   is covered automatically.
2. Add a regression test that fails when the env leaks.
3. Defence in depth: make a report writer refuse a blackboard path outside
   `coga/tasks/` (and outside the repo under test).
4. Strip the polluted `## Dream Skill: validate-drift` sections from the
   surviving non-done tickets. Note that two of the four listed above were
   deleted by the same Dream run's Retro pass, so check which remain before
   editing.

## Related

`recurring-bugs/dream-recipes-write-reports-into-packaged-bootstra` flags exactly
this as its loose end #2 and asks for it to be split out. This ticket is that
split — coordinate so the two do not both fix it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
