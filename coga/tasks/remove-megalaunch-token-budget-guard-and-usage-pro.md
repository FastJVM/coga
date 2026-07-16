---
slug: remove-megalaunch-token-budget-guard-and-usage-pro
title: Remove megalaunch token-budget guard and usage probe
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Remove the megalaunch token-budget guard and the per-agent usage probes
entirely. The guard was built for the old nightly unattended auto-drain;
megalaunch is now on-demand only (attended, human-triggered, each step an
interactive REPL), so "protect the weekly budget in an unattended sweep" no
longer applies. Meanwhile the guard costs a throwaway `codex exec` primer per
sweep and silently rots when codex changes its snapshot format — codex-cli
0.144.4 now emits a single weekly window (`"secondary": null`), which the
probe's parser trips over, so every codex ticket is skipped as
`usage window unreadable` despite ~96% of the weekly window remaining
(observed 2026-07-15 sweep of `install/`, 7/7 skipped-budget).

Scope:

- Delete `src/coga/usage_probe.py` and `tests/test_usage_probe.py`.
- Strip probe wiring, `check_budget` calls, the `skipped-budget` outcome, and
  the `BudgetDecision` plumbing from `src/coga/megalaunch.py` and
  `src/coga/commands/megalaunch.py`.
- Remove the `[megalaunch]` budget fields from `config.py`
  (`min_session_remaining_percent`, `min_weekly_remaining_percent`,
  `weekly_final_window_hours`). Fail-loud config validation means a repo
  still carrying those keys errors; point the message at "delete the key"
  (no-backwards-compat stage posture).
- Update the `coga/cli` context (packaged copy under
  `src/coga/resources/templates/`, plus live `coga/contexts/` override if one
  exists) to drop the budget-guard / `skipped-budget` mentions.
- Prune related tests in `tests/test_megalaunch.py` / `tests/test_config.py`.
- Drop `requests` from dependencies if the probe was its only user.

Accepted tradeoff: a big sweep loses its pacing brake — nothing stops a long
queue from eating the weekly window in one run. That is now a visible,
attended decision by the human running the sweep.

Note: this removes the *pre-launch budget gate* only. Per-session usage
capture (`## Usage` records / `coga usage`) is a separate mechanism and is
not in scope here.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
