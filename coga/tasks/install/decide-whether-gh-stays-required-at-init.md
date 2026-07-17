---
slug: install/decide-whether-gh-stays-required-at-init
title: Decide whether gh stays required at init
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
pr: https://github.com/FastJVM/coga/pull/580
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

## Implemented (commit 582ea84d on gh-optional-at-init)

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

Verification: rebased onto latest origin/main (`fe94e506`), then full suite in
the worktree with `PYTHONPATH=<worktree>/src python3.12 -m pytest -q` →
1221 passed, 1 skipped. `coga validate --task
install/decide-whether-gh-stays-required-at-init --json` → 1 ok, 0 issues.
Branch is clean and 2 commits ahead of origin/main.

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

## Peer review

Native `codex review --base main` found one must-fix contract gap: after init
succeeded without `gh`, the packaged `code/open-pr` and skill-update PR paths
could push and then raise an uncaught `FileNotFoundError`. The branch now
preflights `gh` before an open-PR push and translates a missing executable in
the skill-update PR helper into an actionable install/login error. Regression
coverage was added for both paths in peer-review commit `e1dd41df`; focused
verification passed (160 tests), followed by the post-rebase full suite above.

## PR

Demote the GitHub CLI from an init-time requirement to point-of-need
enforcement, while keeping missing-`gh` failures actionable in managed-skill,
open-PR, autoclose, and skill-update PR flows. Update the init guidance and
dependency tests so Git remains the sole hard prerequisite.

Test plan: `PYTHONPATH=<worktree>/src python3.12 -m pytest -q` (1221 passed,
1 skipped).

## Usage

{"agent":"claude","cache_creation_input_tokens":67100,"cache_read_input_tokens":699708,"cli":"claude","input_tokens":35,"model":"claude-fable-5","output_tokens":5806,"provider":"anthropic","schema":1,"session_id":"be17a8c6-a6c0-4631-965a-612561bf9389","slug":"install/decide-whether-gh-stays-required-at-init","step":"implement","title":"Decide whether gh stays required at init","ts":"2026-07-16T04:16:30.257247Z","usage_status":"ok"}
