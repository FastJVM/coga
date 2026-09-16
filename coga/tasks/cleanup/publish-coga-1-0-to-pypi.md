---
title: Publish coga 1.0 to PyPI
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
step: 2 (human-executes)
---

## Description

Cut the `1.0` release and publish it to PyPI. The owner decided (2026-09-02)
that the launch release is `1.0`, published before marketing post 1 ships.
PyPI currently serves `0.2.0` (plus a 1 KB `0.0.1` placeholder); this repo is
at `0.3.1`. The owner executes the release by hand; the agent briefs first and
verifies read-only afterwards.

## Context

**Why this blocks post 1.** `marketing/phase-0-audit` (step 1, 2026-09-02)
found there is no working first run from PyPI today: 0.2.0's `coga init`
crashes, and 0.3.1's `init` pip-installs its own version from PyPI into the
vendored venv, so a source install cannot `init` until that version exists on
PyPI either. 1.0 on PyPI fixes both by construction.

**Procedure.** `docs/releasing.md` is the contributor-facing runbook: bump
`version` in `pyproject.toml` from `0.3.1` to `1.0.0`, tag, and publish a
GitHub Release; `.github/workflows/release.yml` publishes to PyPI over Trusted
Publishing (no token). The doc recommends a TestPyPI dry run first
(`workflow_dispatch` with target `testpypi`); PyPI uploads are immutable.

**Ordering.** The Python 3.11 fix
(`fix-coga-init-crash-on-python-3-11-by-adding-the-r`) must land on `main`
before this release is cut, or `requires-python` must be raised to 3.12 in the
same release. Without one of the two, `coga init` on 1.0 still crashes on the
documented Python floor.

**Done check.** `uv tool install coga` (or `pip install coga` in a fresh 3.11
venv) yields `1.0.0`, and `coga init --user tester` succeeds in a scratch git
repo. Step 3 of `marketing/phase-0-audit` re-runs the full README quickstart
against it; that run is the one that counts.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Brief (step 1, 2026-09-15, read-only)

### Goal
Publish `coga 1.0.0` to PyPI so a fresh `pip install coga` / `uv tool install coga`
gives a working `coga init` on the documented Python floor (3.11).

### Facts verified today (corrections to the ticket text)
- `pyproject.toml` is at **`0.3.2`**, not `0.3.1` (commit `6e505d81`). The bump
  is `0.3.2 -> 1.0.0`.
- PyPI serves `0.0.1` and `0.2.0` only. No `0.3.x` was ever tagged or released:
  the only git tag and only GitHub Release is `v0.2.0`.
- **The Python 3.11 fix is NOT on `main`.** `src/coga/resources/__init__.py`
  does not exist on `main`. Ticket
  `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` is at step 2
  (peer-review); branch `resources-pkg-init` exists locally with all acceptance
  criteria checked, no PR opened yet. The ordering precondition is unmet.
- The release path is proven: `release.yml` ran green for `v0.2.0`
  (run 28296440460, 2026-06-27) publishing to PyPI over Trusted Publishing, and
  a `testpypi` `workflow_dispatch` succeeded on 2026-06-25. Both GitHub
  environments (`pypi`, `testpypi`) exist. TestPyPI's `coga` project page now
  404s, so a fresh TestPyPI dry run may need the pending publisher re-added
  (docs/releasing.md §1) — optional, not required.
- `init` no longer pip-installs its own version into a vendored venv
  (`init.py` docstring: "init installs no software"), so the ticket's second
  "why" is stale; the 3.11 crash is the real remaining first-run blocker.

### Ordered steps for the owner (step 2)
0. **Land the 3.11 fix first** — recommended over raising `requires-python`.
   Finish `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`
   (peer-review -> open-pr -> merge). The fix is one `__init__.py` plus tests;
   raising the floor to 3.12 instead would be a public compatibility change
   in a 1.0 for no gain. Confirm: `git show main:src/coga/resources/__init__.py`
   prints the docstring.
1. On `main`: set `version = "1.0.0"` in `pyproject.toml`, commit
   (`Bump version to 1.0.0`), push. `coga --version` reads package metadata;
   nothing else in the tree hardcodes the version.
2. *(Optional dry run)* Actions -> Release -> Run workflow -> target
   `testpypi`; then `pip install --index-url https://test.pypi.org/simple/
   --extra-index-url https://pypi.org/simple/ coga==1.0.0` in a fresh 3.11
   venv and run `coga init --user tester` in a scratch git repo. If the
   TestPyPI job fails on auth, re-register the pending publisher per
   docs/releasing.md §1 or skip — PyPI publish itself is already proven.
3. GitHub -> Releases -> Draft a new release: tag **`v1.0.0`**, target `main`,
   Publish release. `release.yml` builds (`uv build`, `twine check`) and
   publishes to PyPI automatically.
4. Watch the run: `gh run list --workflow=release.yml --limit 1`.

### The irreversible action
Step 3. Publishing `1.0.0` to PyPI is permanent: the version can be yanked but
never re-uploaded. Anything wrong in the wheel means the next fix ships as
`1.0.1`. Do not publish before step 0 is on `main`.

### Done check (step 3, agent, read-only)
- `curl -s https://pypi.org/pypi/coga/json | jq .info.version` -> `1.0.0`
- Fresh Python 3.11 venv: `pip install coga` -> `coga --version` prints
  `coga 1.0.0`; `git init /tmp/x && cd /tmp/x && coga init --user tester`
  succeeds and creates `coga/`.
- The run that counts is `marketing/phase-0-audit` step 3's full README
  quickstart against the published 1.0.0.
