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
step: 3 (verify-read-only)
---

## Description

Publish `coga 0.4.0` to PyPI. On 2026-10-02 the owner changed the release
from `1.0.0` to `0.4.0` and explicitly authorized the agent to execute it
in this attended owner-step session. The historical ticket title and path
remain unchanged.

## Context

The release runbook is `docs/contexts/coga/releasing/SKILL.md`. Bump
`pyproject.toml` from `0.3.2` to `0.4.0`, land it on `main`, and publish the
GitHub Release tagged `v0.4.0`; `.github/workflows/release.yml` uploads via
PyPI Trusted Publishing.

The Python 3.11 resource-package fix is now present on `main`:
`src/coga/resources/__init__.py` is tracked. Keep the documented Python 3.11
floor and verify the built wheel and the published package on that version.
The old claim that init installs its own package into a vendored venv is
obsolete.

**Release gate.** Run the full local suite, build and check both distributions,
and verify a fresh Python 3.11 install plus `coga init --user tester` in a
scratch Git repository. The owner explicitly accepted the existing repository
validation error `unsynthesized-draft-blackboard` in `marketing/readme-top`
on 2026-10-02, provided package tests and clean-install checks pass. Leave
that unrelated draft untouched.

**Done check.** A fresh `pip install coga` yields `0.4.0`; `coga --version`,
`coga init --user tester`, and validation succeed in a scratch repository.
The full authenticated README first-task audit remains separate marketing
verification; an install/init check does not claim that audit passed.

<!-- coga:blackboard -->

## Release execution — 2026-10-02 (current)

- Owner authorized agent execution and confirmed `0.4.0`, superseding the
  September `1.0.0` brief below. No owner-step workflow advance requested.
- Release checkout: `/tmp/coga-release-0.4.0`, branch `release-0.4.0`, based on
  `origin/main` at `304167cf5`. PyPI currently has only `0.0.1` and `0.2.0`.
- Python 3.11 wheel smoke passed: version `0.4.0`, init in
  `/tmp/coga-040-wheel-smoke-pst8gnxf`, validation `ok_count: 1`, no issues.
- Both wheel and sdist build and pass `twine check`.
- Initial full suite: 3220 passed, 6 failed. All six failures came from the
  installed-wheel test helper patching deleted `_check_external_dependencies`.
  Updated it to patch `_require_init_tools` and `_offer_optional_tools`, matching
  the existing packaging test. Runtime package behavior is unchanged.
- Final release gate: `PYTHONPATH=/tmp/coga-release-0.4.0/src
  /home/n/Code/codex/coga/.venv/bin/python -m pytest -q` -> **3226 passed**
  in 297.08s (Python 3.12.12).
- `/home/n/Code/codex/coga/.venv/bin/python -m hatchling build` and
  `/tmp/coga-release-wheel-venv/bin/python -m twine check dist/*` -> both
  distributions passed. Built wheel installed using Python 3.11.15.
- `PYTHONPATH=/tmp/coga-release-0.4.0/src
  /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json` ->
  212 valid tickets, one existing error (`marketing/readme-top` unsynthesized
  draft blackboard), explicitly accepted by the owner. Scoped release-ticket
  validation passed with only the isolated checkout's missing-user warning.
- Published **0.4.0** from `7cccb27e47dff7f0f8ee1e2bae61a3ab0a564c6e`:
  https://github.com/FastJVM/coga/releases/tag/v0.4.0 . The release commit was
  rebased over concurrent ticket-state-only changes; source and tests were
  unchanged from the passing gate.
- Trusted Publishing succeeded:
  https://github.com/FastJVM/coga/actions/runs/37041169165 . Both artifacts
  are live at https://pypi.org/project/coga/0.4.0/ . Wheel SHA256:
  `ba57ac7b7e9fc73af75dfe3bec7ac7569f03ca0af0f9aed929827bc5b680d564`;
  sdist SHA256:
  `da9c8e3c35152a51deed28417f7ee2007d150249cda1295dd8ce4f677036f7fa`.
- Fresh published-package gate passed on Python 3.11.15:
  `python3.11 -m venv /tmp/coga-pypi-0.4.0-final-venv`, then
  `/tmp/coga-pypi-0.4.0-final-venv/bin/python -m pip install --no-cache-dir
  --index-url https://pypi.org/simple coga` installed **0.4.0** without a pin.
  Its `coga --version` printed `coga 0.4.0`; `coga init --user tester` and
  `coga validate --json` passed (`ok_count: 1`, no issues), with clean Git
  status in `/tmp/coga-040-pypi-smoke-62g6_rrq`.
- The first immediate post-upload unpinned install still saw cached 0.2.0;
  a new fresh environment after index refresh obtained 0.4.0. Receipts:
  `/tmp/coga-pypi-0.4.0-final-install.log`,
  `/tmp/coga-pypi-0.4.0-final-smoke.log`,
  `/tmp/coga-release-0.4.0-pytest-fixed.log`.
- Release execution is complete. Owner-step transition remains unrequested;
  no bump performed. The next workflow step's independent verification and
  the marketing full authenticated first-task audit remain separate.


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
