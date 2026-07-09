---
slug: install/init-venv-python-selection-breaks-on-wrong-host-py
title: Init venv python selection breaks on wrong host python
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/with-review
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
