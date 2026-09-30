---
title: Uninstall has no removal path for the preferred uv tool install
status: in_progress
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
step: 2 (peer-review)
agent: claude
---

## Description

Filed by Dream 2026-W40, Phase 6 (shard ks-29, class stale, target `docs/contexts/coga/uninstall/SKILL.md`). `coga/install` makes `uv tool install coga` the preferred install and sends removal to `coga/uninstall`, but uninstall knows only pipx and pip: without `--purge` it prints `pipx uninstall coga` / `pip uninstall coga`; with `--purge` a non-pipx CLI runs `<python> -m pip uninstall -y coga`. That matches `src/coga/commands/uninstall.py::_handle_package`, which branches on `commands/update.py::running_cli_location()` (whose docstring lumps "pip / uv tool / system python" into `"other"`). A uv tool environment normally has no pip, so `--purge` on the recommended install path fails and prints another failing `-m pip` hint; nothing names `uv tool uninstall coga`. Fix: detect a uv tool venv (e.g. `uv-receipt.toml` in the venv root) like pipx, print/run `uv tool uninstall coga`, and update the topic plus its packaged twin. Needs code review, hence code/with-review. No open ticket mentions `uv tool uninstall`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: uninstall-uv-tool

Plan: add a `"uv"` kind to `update.running_cli_location` (marker `uv-receipt.toml` in the venv root, same unresolved-venv rule as pipx); `uninstall._handle_package` runs/prints `uv tool uninstall coga` for it; no-purge hint lists uv first; update `coga/uninstall` topic + packaged twin.

## Handoff (implement)

Commit `Uninstall a uv tool install through \`uv tool uninstall\`` pushed on `uninstall-uv-tool`.

- `src/coga/commands/update.py` `running_cli_location`: new kind `"uv"` when `uv-receipt.toml` sits in the unresolved `sys.executable` venv root (checked after pipx). Its only caller is `uninstall._handle_package`; `coga update` does not use it.
- `src/coga/commands/uninstall.py`: `_handle_package` sends pipx and uv through a new shared `_uninstall_via_tool(tool, subcommand)` (which lookup → run → print the same installer's manual command if it's missing or fails). The no-purge hint now lists `uv tool uninstall coga` first. One side effect: pipx's failure hint used to wrongly print `pip uninstall coga` and now prints `pipx uninstall coga`.
- Tests: `test_running_cli_location_detects_uv_tool` (test_init.py); `test_uninstall_purge_runs_uv_tool_for_uv_install` and `..._uv_install_without_uv_prints_uv_hint`; the no-purge test now asserts both the uv and pipx lines.
- The topic `coga/uninstall` "The global package" section and its bootstrap twin are updated and byte-identical.
- Verified: `.venv/bin/python -m pytest -q` → 3138 passed. The system `python` lacks `tomlkit`, so use `.venv`.
- Nothing is left unresolved. No example fixture change is needed because uninstall does not touch the task layout or composition.
