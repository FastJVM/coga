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
step: 3 (open-pr)
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

## Peer review

- `codex review --base main` returned successfully with no must-fix findings. It verified uv detection, installer-specific removal, and synchronized documentation; its targeted suite passed 156 tests. Review log: `/tmp/coga-uninstall-uv-review.log` (ephemeral).
- Rebased unconditionally with `git fetch origin main && git rebase FETCH_HEAD`; no conflicts or code corrections were needed. Pushed commit `d17870f96` with `git push --force-with-lease -u origin uninstall-uv-tool`. Returned to clean `main`, equal to `origin/main`.
- Full verification after rebase: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q` → **3138 passed in 245.65s**. `git diff --check main...HEAD` passed on the feature branch.
- Drove `python -m coga.cli uninstall` in an 80×24 PTY against a disposable `/tmp/coga-uninstall-uv-terminal` footprint: answered the confirmation prompt, observed local removal and all three manual commands with `uv tool uninstall coga` first. Checked `uninstall --help` in a PTY as well. Actual global removal was covered by subprocess assertions, not performed against the operator's installed CLI.
- No outstanding findings or design decisions. Ready for the mechanical open-pr step.

## PR

`coga uninstall --purge` now recognizes a uv tool environment by its `uv-receipt.toml` marker and runs `uv tool uninstall coga`, avoiding the pip invocation that fails in the preferred install's pip-less environment. Ordinary uninstall lists the uv removal command first, and missing or failing tool installers retain their own manual removal command (including the corrected pipx failure hint).

Updates the uninstall contract and its packaged twin, with regression coverage for uv detection, purge dispatch, and missing-uv guidance.

Test plan: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q` — 3138 passed; Codex review returned without findings; disposable PTY confirmation/removal and help smoke checks passed.
