---
slug: remote-default-origin
title: remote-default-origin
status: done
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
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
---

## Description

A user with a non-standard remote name (upstream instead of origin) found Relay assumes origin when pushing — it works for the default case but silently breaks for anyone with a different layout.
Make the remote name configurable (e.g. remote = "origin" in relay.toml, defaulting to origin) instead of hardcoded.
Sweep the one hardcoded push in skill_manager.py plus any skill prompts that say origin, and have them use the configured name.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: remote-default-origin
worktree: ../relay-remote-default-origin
pr: https://github.com/FastJVM/relay/pull/406

- Pushed branch to origin and opened PR #406. `gh pr checks 406` reports no CI
  checks configured for this repo, so there is no green/red gate to wait on.

## Findings

- The configurable infrastructure already existed before this ticket:
  `Config.git_remote` is parsed from `[git].remote` (default `origin`) in
  `config.py:_parse_git`, and `git.py`, `digest.py`, `recurring.py`,
  `validate.py`/`github_preflight.py` already use `cfg.git_remote`.
- The only true hardcoded push the ticket names was `skill_manager.py`
  `open_or_update_pr` (`git push --force-with-lease -u origin <branch>`).
- Skill prompts (`code/open-pr`, `dev/code` context, etc.) say "push the
  branch" generically — none hardcode `origin`, so there was nothing to
  sweep in the prompts. Remaining `origin` mentions in `git.py` are
  comments/docstrings, not commands.

## Change

- `skill_manager.open_or_update_pr` gains a `remote: str = "origin"` kwarg
  and uses it in the push.
- The one caller, `run_skill_update_pr_flow`, passes `cfg.git_remote`.
- Regression test `test_dream_pr_summary_pushes_to_configured_non_origin_remote`
  in `tests/test_skill_manager.py`: with `[git] remote = "upstream"`, the
  push uses `upstream` and no git command mentions `origin`.

## Test status

- `python3.12 -m pytest tests/test_skill_manager.py` → 33 passed.
- Full suite: 807 passed, 1 skipped, **2 failed** in
  `tests/test_autoclose_sweep.py`
  (`..._live_and_packaged_copies_stay_in_sync`,
  `..._recurring_template_creates_idempotently`). These are PRE-EXISTING and
  fail identically on `main` — they assert a hardcoded
  `last_serviced_period` date that drifts with the current date
  (expected `2026-06-11`, got `2026-06-17`). Unrelated to this change; not
  masked, just noted.
- Note: repo needs Python 3.11+ (`tomllib`); use `python3.12` here.

## Peer Review

- Ran required `codex review --base main` from `../relay-remote-default-origin`.
  First sandboxed run failed before review with read-only app-server init; reran
  outside the sandbox and Codex reported no actionable regressions.
- During the review sweep, found one additional hardcoded push in the packaged
  Dream `validate-drift` helper:
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/tasks/validate-drift/run.py`
  used `git push -u origin HEAD` when setting upstream for a repair branch.
- Applied peer-review fix in commit `c2d1617`:
  `commit_and_push_fixes` now accepts `remote: str = "origin"`, and the script
  passes `load_worker_config(...).git_remote` for `--commit-and-push`.
- Added coverage in `tests/test_dream_validate_drift.py` for the no-upstream
  fallback push using `upstream`, plus `main()` wiring from config.

## Peer Review Test Status

- `PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest -p no:cacheprovider tests/test_skill_manager.py tests/test_dream_validate_drift.py`
  -> 42 passed.
- `PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest -p no:cacheprovider`
  -> 809 passed, 1 skipped, **2 failed** in `tests/test_autoclose_sweep.py`.
  Same unrelated autoclose `last_serviced_period` drift as the implementation
  handoff (`expected 2026-06-11`, got existing `2026-06-17`).
