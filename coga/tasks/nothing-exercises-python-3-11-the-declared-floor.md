---
title: Nothing exercises Python 3.11, the declared floor
status: blocked
owner: nicktoper
agent: claude
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
---

## Description

`pyproject.toml` declares `requires-python = ">=3.11"`, but nothing runs the
suite on 3.11. `.github/workflows/` contains only `release.yml`, a PyPI publish
workflow with no pytest step, and `coga/testing` (`docs/contexts/coga/testing/SKILL.md`,
formerly part of `coga/codebase`) tells
the reader to run `PYTHONPATH=$PWD/src python3.12 -m pytest` because the ambient
`python3` is often 3.9. That guidance is correct about 3.9 and silently makes
the declared floor untested.

The cost is already on record. `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`
found that `coga init` — the first command a new user runs — crashed on every
3.11 interpreter with `TypeError: MultiplexedPath.joinpath() takes 2 positional
arguments but 3 were given`, because `src/coga/resources/` shipped no
`__init__.py` and `importlib.resources.files()` returns a `MultiplexedPath`
(single-segment `joinpath`, no `__fspath__` before 3.12) for a namespace
package. The ticket says outright that "3.12 happens to work, which is why the
break stayed invisible in local development and CI", and it affected five call
sites across `paths.py`, `update.py`, `managed_skills.py` and
`dream_cleanup_orphan_markers.py`. The same ticket notes that
`src/coga/commands/__init__.py` leaves the identical namespace-package footgun
latent.

## Context

Two things are wanted and they are separable:

1. A real 3.11 verification step, so the declared floor is exercised rather
   than assumed. There is no test CI workflow at all today, which is the larger
   half of this.
2. The rule written into its owning topic — `coga/codebase/gotchas`
   (`docs/contexts/coga/codebase/gotchas/SKILL.md`) for the package-marker
   hazard and `coga/testing` for what a green run proves — and their
   enforced packaged twins: never add a new `files("coga.<pkg>")` consumer
   without a package marker, and a green 3.12 run is not evidence for the
   declared floor.

If the floor is not going to be tested, the honest alternative is to raise
`requires-python` — but that is an owner decision, not an implementer's.

Environment note from this Dream run: `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`
currently fails on this machine for an unrelated reason (`hatchling` is not
importable by the ambient interpreter), which is worth knowing before anyone
reads a red suite as evidence here.

<!-- coga:blackboard -->

## Dev

branch: ci/python311-floor
worktree: /home/n/Code/codex/coga-ci-python311
pr: https://github.com/FastJVM/coga/pull/894

Re-ported onto main 2026-09-24 in an orient session (old commit 28541821b was
624 commits behind): guidance now lives in coga/testing and coga/packaging, and
PR #894 also exempts the phone-home ticket's live `period_state` from the twin
check. Local 3.11 run: 2933 passed + packaging suite green after the exemption.

## Implementation plan

- Add a small GitHub Actions matrix for Python 3.11 and 3.12 on pull requests
  and pushes to main. Install `.[test]`, then run the complete pytest suite,
  including the wheel build; preserve the declared `>=3.11` floor.
- Update the codebase context and its packaged twin: use an explicit 3.11
  verification command, require package markers for resource anchors, and
  replace the obsolete publish-only CI posture. Link the owning guidance
  from the contributor documentation.
- Keep implementation changes in the recorded feature checkout; write task
  state and perform the terminal transition from this primary checkout.

## Findings

- `pyproject.toml` already declares both pytest and hatchling in the test
  extra; the normal editable test install supplies the wheel test backend.
- The referenced resource fix is still awaiting review/merge:
  `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`, PR
  https://github.com/FastJVM/coga/pull/831. The freshly fetched main still
  lacks `src/coga/resources/__init__.py`. The actual 3.11 failure was
  reproduced below; this branch does not duplicate that ticket's source fix.

## Changes

- `.github/workflows/tests.yml`: Python 3.11/3.12 jobs for pull requests and
  pushes to main, read-only repository permissions, explicit interpreter
  selection, `python -m pip install -e ".[test]"`, absolute source
  `PYTHONPATH`, and `python -m pytest`. Both jobs run even if one fails.
- `coga/contexts/coga/codebase/SKILL.md` and its packaged twin now require
  package markers for `files("coga.<pkg>")` anchors and verification on the
  declared floor, and describe the test workflow separately from publishing.
- `docs/development.md` creates the example venv with Python 3.11 and links
  to the owning verification/resource guidance. No runtime, fixture,
  configuration, or release-workflow changes.
- Action versions and inputs checked against the official
  https://github.com/actions/setup-python and
  https://github.com/actions/checkout documentation.

## Verification

- Fresh Python 3.11.15 venv `/tmp/coga-python311-ci-venv` successfully
  installed `.[test]` after network access was granted for the package index.
- Workflow YAML structure, matrix, commands, declared `>=3.11` floor,
  feature-checkout import resolution, and context byte identity checked.
- `PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  — Python 3.12.12: **2655 passed** in 205.62 seconds, exit 0; log
  `/tmp/coga-python311-ci-py312.log`.
- `PYTHONPATH="$PWD/src" /tmp/coga-python311-ci-venv/bin/python -m pytest`
  — Python 3.11.15: **426 failed, 2229 passed** in 257.99 seconds, exit 1;
  log `/tmp/coga-python311-ci-py311.log`. Resource lookups raise the known
  `MultiplexedPath.joinpath` error; CLI tests also fail downstream of those
  lookups. All 11 packaging tests passed on both interpreters, including the
  wheel build. This is not the earlier missing-Hatchling environment error.
- The unchanged primary checkout independently reproduces the resource bug:
  `PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-python311-ci-venv/bin/python -c 'from coga.paths import packaged_template_path; print(packaged_template_path("bootstrap", "contexts"))'`
  raises `TypeError: MultiplexedPath.joinpath() takes 2 positional arguments
  but 5 were given`. The failing symbol is `paths.packaged_template_path`
  in `src/coga/paths.py`. The same call succeeds on 3.12 against the feature
  checkout; this branch changes no Python implementation or tests.

## Commit

- `28541821` — `Exercise Python 3.11 and 3.12 in test CI`.
- `git fetch origin main` followed by `git rebase FETCH_HEAD` confirmed the
  branch is current with `a0a18ffa`; no new commits arrived.
- `git diff --check origin/main...HEAD` passed; feature checkout is clean.
  No branch push or PR was performed.

## Dependency handoff

Implementation is committed, but the implement step cannot meet its green-suite
acceptance until `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`
lands. PR https://github.com/FastJVM/coga/pull/831 was rechecked after both
suites and remains open, with no merge commit. Per `code/implement`, unrelated
test failures must be recorded and escalated rather than masked.

Merge that resource-package fix, then resume this task in the recorded feature
worktree, fetch/rebase main, and rerun both full-suite commands above. Do not
skip the failing 3.11 tests or raise the Python floor. If both suites pass,
update these results and run `coga bump` from the primary checkout to complete
implement. The queued dependency reason must contain the exact path-qualified
slug above so megalaunch can recognize its completion.

---

## Blockers

- [ ] [2026-09-18 11:04] [agent:claude] id=20260918T110453 Merge PR #831 for cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r, then resume this implement step to rebase and rerun both suites. Current main reproduces the Python 3.11 MultiplexedPath.joinpath crash: 426 failed, 2229 passed; Python 3.12 has 2655 passed. CI and guidance changes are committed as 28541821 on ci/python311-floor.

---

## Blocker reminders

- e780f0b1218a last_reminded: 2026-09-21 08:55
