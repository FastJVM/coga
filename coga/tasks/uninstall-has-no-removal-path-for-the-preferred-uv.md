---
title: Uninstall has no removal path for the preferred uv tool install
status: draft
owner: nicktoper
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

Filed by Dream 2026-W40, Phase 6 (shard ks-29, class stale, target `docs/contexts/coga/uninstall/SKILL.md`). `coga/install` makes `uv tool install coga` the preferred install and sends removal to `coga/uninstall`, but uninstall knows only pipx and pip: without `--purge` it prints `pipx uninstall coga` / `pip uninstall coga`; with `--purge` a non-pipx CLI runs `<python> -m pip uninstall -y coga`. That matches `src/coga/commands/uninstall.py::_handle_package`, which branches on `commands/update.py::running_cli_location()` (whose docstring lumps "pip / uv tool / system python" into `"other"`). A uv tool environment normally has no pip, so `--purge` on the recommended install path fails and prints another failing `-m pip` hint; nothing names `uv tool uninstall coga`. Fix: detect a uv tool venv (e.g. `uv-receipt.toml` in the venv root) like pipx, print/run `uv tool uninstall coga`, and update the topic plus its packaged twin. Needs code review, hence code/with-review. No open ticket mentions `uv tool uninstall`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
