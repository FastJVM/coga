---
slug: install/init-venv-python-selection-breaks-on-wrong-host-py
title: Init venv python selection breaks on wrong host python
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

`install_venv` builds the vendored `.coga/.venv` with `sys.executable` — the
Python that happens to be running the coga CLI. That inherits whatever
interpreter the install method chose (uv-managed Python, pipx's, system
`python3`), and the owner hit a wrong-Python/3.12 failure on a real machine.
Known sharp edges: an interpreter that pip accepted but the vendored build
chokes on; Debian/Ubuntu system Pythons without `python3-venv`/ensurepip
(venv creation fails); and host-Python upgrades leaving the venv rebuilt
against a different X.Y than expected. Make the interpreter choice explicit
and validated: check `sys.version_info` against the vendored copy's
`requires-python` before building, prefer a stable resolution rule (document
it), and fail with the exact remediation when venv/ensurepip is missing.

## Context

Reported by nicktoper (2026-07-09) after the fresh-container retest — exact
repro from his machine still to be captured on this ticket. Touchpoint:
`src/coga/commands/update.py` (`install_venv`, `_venv_python_version`).
Related: `install/vendor-cli-from-installed-package-not-git-clone` changes
what gets installed into this venv (PyPI wheel instead of clone) but keeps
the venv itself, so the interpreter-selection question survives that ticket.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/530
branch: venv-python-selection
worktree: /home/n/Code/claude/coga/.coga/worktrees/coga-venv-python-selection

## Implemented (commit c82c0f6e on venv-python-selection)

All in `src/coga/commands/update.py`; tests in `tests/test_init.py` next to
the existing venv-recreation block, same monkeypatched-`subprocess.run` style.

1. **Explicit, documented resolution rule** — new `resolve_venv_python()`:
   (1) `$COGA_PYTHON` if set (path or PATH name via `shutil.which`; exits 2
   if it doesn't resolve — an explicit choice never silently falls back),
   else (2) `sys.executable`, the interpreter running the coga CLI. Rule
   documented in the function and `install_venv` docstrings. `COGA_PYTHON`
   is the escape hatch for "pip accepted this Python but the vendored build
   chokes on it" — a requires-python check alone can't catch a too-new
   interpreter that the spec still admits.
2. **Validate before building** — `_requires_python_spec()` parses
   `requires-python` from the vendored pyproject (stdlib `tomllib`);
   `_version_satisfies()` is a minimal PEP 440 clause matcher
   (`>= > <= < == != ~=` + `.*` wildcards on ==/!=; unparseable clauses
   count as satisfied so an exotic spec can't brick the bootstrap — pip
   re-checks at install time). Rejection names the spec, the interpreter
   path/version, and the `COGA_PYTHON=` remediation, and happens before any
   venv is created or removed.
3. **ensurepip remediation** — when `python -m venv` fails and stderr
   mentions ensurepip, the error appends
   `sudo apt install python3.X-venv` (X.Y from the chosen interpreter) or
   "set COGA_PYTHON to a Python with venv support".
4. **Rebuild check follows the chosen interpreter** — recreate-on-X.Y-
   mismatch now compares `pyvenv.cfg` against the *resolved* python's
   version, not blindly `sys.version_info`.

Verification:
- `python3.12 -m pytest` (with `PYTHONPATH=src`): 1135 passed, 1 skipped.
- E2E on this host: `COGA_PYTHON=<miniconda 3.9>` → rejected pre-build with
  "Python 3.9.12 … does not satisfy … (>=3.11)" + remediation, exit 2.
  `COGA_PYTHON=python3.12` → real venv built (pyvenv.cfg 3.12.12), vendored
  CLI pip-installed and executable.

Notes for reviewer:
- Pre-existing, unrelated: `test_launch_script.py::test_bootstrap_script_
  launch_is_stateless` fails when `coga` isn't installed in the running
  interpreter (pytest's `pythonpath = ["src"]` doesn't reach subprocesses);
  fails identically on unmodified main, passes with `PYTHONPATH=src`
  exported. Not caused by this change; possible follow-up: export it from
  the test or conftest.
- Debian's own venv-failure stderr already suggests the apt package; our
  remediation keys on "ensurepip" in stderr, so it's additive and also
  covers non-Debian pythons with stripped ensurepip.

## Peer Review

Native `codex review --base main` was rerun outside the sandbox after the
known read-only app-server startup failure. It found one must-fix: an existing
venv from a different interpreter with the same X.Y caused an explicit
`COGA_PYTHON` override to be silently ignored.

Fixed in commit `9b967200`: an explicit override now compares the selected
interpreter's resolved executable identity with `pyvenv.cfg` and rebuilds on
mismatch (or when old metadata cannot prove a match). Added regression coverage
and documented the durable rule in `coga/codebase`.

Verification:
- `PYTHONPATH=$PWD/src python3.12 -m pytest tests/test_init.py -q` — 94 passed.
- `PYTHONPATH=$PWD/src python3.12 -m pytest -q` — 1137 passed, 1 skipped.
- `git diff --check main...HEAD` — clean.
- `git merge-tree <merge-base> main HEAD` — clean merge; no conflicts.
- `coga validate --task install/init-venv-python-selection-breaks-on-wrong-host-py
  --json` — clean (`ok_count: 1`, no issues) after the owner authorized creating
  this launch checkout's missing machine-local user config.

## PR

Make the interpreter that builds `.coga/.venv` explicit and fail early: honor
`COGA_PYTHON` before falling back to the running CLI's Python, validate the
choice against the vendored `requires-python`, rebuild when either X.Y or an
explicit interpreter identity changes, and give exact `venv`/`ensurepip`
remediation. The interpreter contract is documented in `coga/codebase`.

Test plan: `PYTHONPATH=$PWD/src python3.12 -m pytest -q` (1137 passed, 1 skipped).
