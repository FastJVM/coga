---
slug: install/decide-whether-gh-stays-required-at-init
title: Decide whether gh stays required at init
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- dev/code
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
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

`gh` is hard-required at `coga init` (`required_at_init=True` in the
dependency manifest) even for users who never open PRs — a new install
burden Greg's original attempt didn't have. It is defensible (PR workflows
and managed skills both use it, and the check is explicit with an install
hint), but it deserves a deliberate decision: keep as-is, or demote `gh` to
point-of-need enforcement like `op` (managed skills already degrade to
warn-only when `gh skill` can't run, and `coga validate --check-github` /
launch preflight cover the PR path). Decide and either document the
rationale in the dependencies manifest or flip the flag.

## Context

Raised by the 2026-07-08 fresh-container retest (bare machine: the very
first `coga init` fails until both git and gh are installed). Touchpoint:
`src/coga/dependencies.py`; README External CLI Tools section (once it
exists — see `install/document-where-to-run-init-and-adopt-existing-repo`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: gh-optional-at-init
worktree: ../coga-gh-optional-at-init

## Decision

Demote `gh` to point-of-need enforcement (`required_at_init=False`), matching `op`.

Rationale (from reading the code, not just the ticket):
- The only thing `gh` actually gates at init is optional managed-skill installs, and
  that path already degrades to warn-only: `install_managed_skills` catches
  `GhSkillUnavailableError`, records one skip note with an install hint, and every
  skill in `managed-skills.toml` is `required = false`. A fresh init without `gh`
  still prints a visible warning listing the skipped skills.
- Every other `gh` consumer fails loud at point of need with an actionable message:
  `code/open-pr` recipe (attaches `check_gh_auth` setup hints), the autoclose sweep
  (`GhError: gh not found on PATH` — never swallowed even in quiet mode),
  `coga skill` (`GH_SKILL_REQUIRED` install/upgrade hint), branch sweep.
- Proactive coverage for the PR path exists without the init gate:
  `coga validate --check-github` probes gh-installed/gh-auth; `coga launch`
  preflights git push auth before flipping any state.
- Precedent: `op` uses exactly this model with the same documented rationale.
- Concrete pain fixed: the 2026-07-08 fresh-container retest — bare-machine
  `coga init` failed until both git and gh were installed, burdening installs that
  never open PRs. `git` stays hard-required (state storage; nothing works without it).

## Implemented (commit e556645b on gh-optional-at-init)

1. `src/coga/dependencies.py`: `gh` flipped to `required_at_init=False`; its `purpose`
   now documents the point-of-need rationale (mirrors `op`'s entry).
2. `src/coga/commands/init.py`: `_check_external_dependencies` docstring updated —
   only `git` is enforced at init; `gh`/`op` rationale points at the manifest entries.
3. `README.md` Getting Started: "Install Git first; `coga init` requires it" — `gh`
   described as recommended, enforced where used.
4. `tests/test_init.py`: `test_dep_check_crashes_on_missing_gh` →
   `test_dep_check_ignores_missing_gh` (must not raise);
   `test_dep_check_reports_all_required_missing_together` →
   `test_dep_check_omits_optional_tools_from_crash`; the bail-before-scaffolding
   test now uses a missing `git`.

Verification: full suite in the worktree with
`PYTHONPATH=<worktree>/src python3.12 -m pytest` → 1207 passed, 1 skipped.
Branch rebased-checked against origin/main (already up to date).

Notes for reviewers / follow-ups:
- No context/template changes needed: nothing under `coga/contexts` or the packaged
  templates states that `gh` is required at init (checked by grep).
- Observed once during full-suite runs: `tests/test_usage_probe.py::
  test_codex_probe_primes_once_across_reads` failed under full-suite ordering, passed
  alone and on an immediate full-suite rerun, and is untouched by this diff — looks
  like a pre-existing order-dependent flake worth a follow-up ticket.
- Grep note: `coga launch` script-mode runs `run.py` scripts with `sys.executable`;
  when testing from a non-installed tree, PYTHONPATH must be absolute or the spawned
  script can't import `coga` (that was a test-harness artifact here, not a bug).
