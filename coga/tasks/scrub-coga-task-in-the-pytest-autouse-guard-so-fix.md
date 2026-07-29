---
slug: scrub-coga-task-in-the-pytest-autouse-guard-so-fix
title: Scrub COGA_TASK_* in the pytest autouse guard so fixture reports cannot reach
  live tickets
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
step: 2 (peer-review)
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

## Dev

branch: scrub-launch-env
worktree: /home/n/Code/claude/coga-scrub-launch-env

## Plan (implement step)

1. Autouse guard clears the whole launch-owned namespace, derived from
   `coga.task_env.TASK_ENV_KEYS` (not hand-listed) plus the supervisor set
   already there.
2. New `tests/test_env_isolation.py`: an in-suite assertion that no
   launch-owned var is set during a test, plus a nested-pytest subprocess that
   runs that same nodeid with the full namespace polluted — the guard is the
   only reason it can pass.
3. Defence in depth on the reading side: `blackboard_from_env` gains an
   optional coga-OS-root argument and refuses a blackboard outside
   `<root>/tasks/`; the three recipe call sites pass the root they actually
   operate on.
4. Strip the 3 fixture-report sections from
   `ship-a-shared-recurring-reminder-engine-battery.md`.

## Findings

- **Scope item 3 is only half-done on `main`.** `blackboard_from_env` already
  refuses a path with no `tasks/` ancestor (landed in #671 for the packaged
  bootstrap ticket), but the leaked path in *this* bug is
  `<live repo>/coga/tasks/<slug>.md` — it passes that check. The missing half
  is the ticket's "and outside the repo under test", which needs the root the
  recipe is actually operating on, not the (equally leaked) env var.
- **`COGA_SKILL_*` no longer exists.** The pair named in the ticket scope was
  removed by `755e60de Delete the script-seam (#670)`; nothing in `src/` sets or
  reads a `COGA_SKILL_*` variable now. Deriving the guard's list from
  `TASK_ENV_KEYS` is the durable answer — a re-added variable is covered without
  a second edit here.
- **Only 1 of the 4 polluted tickets survives.** `make-sure-we-can-drop-new-recurring-tickets`,
  `install/short-notice-instead-of-raw-git-error-when-sync-ha`, and
  `agree-the-core-vs-skills-move-list-then-execute` are gone (Retro pass).
  `ship-a-shared-recurring-reminder-engine-battery.md` (`status: canceled`,
  so surviving and not done) still carries 3 sections. The
  `## Dream Skill: validate-drift` section in `recurring/dream/ticket.md` is a
  *real* report (real task, real fence fix) — leave it.
## Implemented (commit `ad9a7788`)

1. `tests/conftest.py`: `LAUNCH_OWNED_ENV = (sentinel, COGA_SUPERVISED, expected
   task/step, *TASK_ENV_KEYS)`; `_clear_supervised_session_env` loops over it.
2. `tests/test_env_isolation.py`: (a) the in-suite assertion that no
   launch-owned var is set during a test, (b) a structural check that the guard
   covers all of `TASK_ENV_KEYS`, (c) a child `pytest` run of (a) with every
   launch-owned var pointed at a stand-in outer ticket. **Verified the proof
   bites**: weakening the guard to its old four vars and re-running with
   `COGA_TASK_BLACKBOARD` set fails (a) and (c).
3. `blackboard_from_env(coga_os_root=None)` + `discover_coga_os_root(cwd)` in
   `task_env.py`; refuses a blackboard outside `<root>/tasks/`. `validate-drift`
   and `skill-update` pass `discover_coga_os_root(args.cwd)`,
   `cleanup-orphan-markers` passes the `coga_os` it scanned. `None` root (a unit
   test against a bare tmp dir) skips the containment check rather than refusing
   what it cannot judge. New subprocess regression
   `test_worker_refuses_blackboard_from_another_checkout`.
4. Stripped the 3 sections from `ship-a-shared-recurring-reminder-engine-battery.md`.
5. Amended the `coga/codebase` hazard bullet: the remedy is now enforced, names
   `TASK_ENV_KEYS` as the single list to extend, and warns off re-adding per-test
   opt-outs. No packaged twin of that context exists, so nothing to sync.

Verification: `python -m pytest` → 1538 passed, 1 skipped (python3.12; the repo's
`.venv` has no pytest). `coga validate --json` reports 23 pre-existing repo-state
issues (stuck-in-progress, unknown-assignee, missing-user) — all present on
`main`, none from this diff.

## Notes for review

- The child-`pytest` test is the first nested pytest run in the suite. It selects
  a single nodeid (no recursion) and adds ~1s. The alternative — a plain
  in-process assertion — passes vacuously on a dev machine outside a launch,
  which is exactly how this bug hid.
- `discover_coga_os_root` swallows only `ConfigError`.

- **The in-process leak path** was `test_commit_and_push_main_passes_configured_remote`,
  which calls `run_validate_drift_recipe` directly; its two per-test
  `monkeypatch.delenv` lines are the "remember to do it" pattern the context
  warns about and become redundant once the guard covers the namespace.
