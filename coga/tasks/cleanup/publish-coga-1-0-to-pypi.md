---
slug: cleanup/publish-coga-1-0-to-pypi
title: Publish coga 1.0 to PyPI
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: human
  - name: verify-read-only
    skills: []
    assignee: agent
secrets: null
step: 1 (brief-and-hand-off)
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
