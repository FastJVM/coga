---
slug: fix-coga-init-crash-on-python-3-11-by-adding-the-r
title: Fix coga init crash on Python 3.11 by adding the resources package init
status: draft
owner: nick
human: nick
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
secrets: null
step: 1 (implement)
---

## Description

`coga init` crashes on Python 3.11 on every version, including the current
checkout, with `TypeError: MultiplexedPath.joinpath() takes 2 positional
arguments but 3 were given` (raised from `packaged_template_root` in
`src/coga/paths.py`). Add `src/coga/resources/__init__.py` so the package
resources resolve as a regular package, and add a regression test that runs
on 3.11.

## Context

**Cause** (from `marketing/phase-0-audit`, step 1, 2026-09-02).
`src/coga/resources/` has no `__init__.py`, so
`importlib.resources.files("coga.resources")` returns a namespace-package
`MultiplexedPath`. Its multi-argument `joinpath(*parts)` only exists from
Python 3.12; on 3.11 it accepts a single child. `pyproject.toml` declares
`requires-python = ">=3.11"` and `docs/getting-started.md` says "Python
3.11+", so the documented floor does not work. The owner's own install runs on
3.12 (uv tool python), which is why nobody hit it.

**Scope.** Ship the `__init__.py` (check that packaging still includes the
templates and `bootstrap/` resources: `uv build` and inspect the wheel), then
grep for every other `files("coga.resources")` / `files("coga...")` call
(`paths.py`, `managed_skills.py`, `dream_cleanup_orphan_markers.py`, and any
others) and make sure none relies on the 3.12-only multi-arg `joinpath`.
Alternative if the fix is worse than it looks: raise `requires-python` to
`>=3.12` and update both docs; the owner prefers the fix. Record which one
landed on the blackboard.

**Verification.** Run the test suite under a 3.11 interpreter (`uv run
--python 3.11 -m pytest`), and `coga init --user tester` in a scratch git repo
under a 3.11 venv installed from this checkout (set
`COGA_REPO_URL=/path/to/checkout` so init does not pull from PyPI).

**Ordering.** Must land before `publish-coga-1-0-to-pypi` cuts the release.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
