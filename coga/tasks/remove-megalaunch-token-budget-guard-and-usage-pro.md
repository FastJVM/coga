---
slug: remove-megalaunch-token-budget-guard-and-usage-pro
title: Remove megalaunch token-budget guard and usage probe
status: done
owner: nicktoper
human: nicktoper
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

## Dev

branch: remove-budget-guard
worktree: /home/n/Code/claude/coga-remove-budget-guard

## Plan (implement step, 2026-07-15)

Survey findings:

- `requests` is also used by `src/coga/validate.py` (Slack webhook check) and
  `src/coga/notification/slack.py`, so the dependency **stays** in
  pyproject.toml despite the probe deletion.
- No live `coga/contexts/coga/cli` override exists — only the packaged copy
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
  mentions the budget guard (two spots: the sweep description and the
  outcome list).
- Neither the repo's own `coga.toml` nor `example/coga/coga.toml` carries a
  `[megalaunch]` section, so no fixture config changes needed.
- config.py has precedent for dedicated migration errors that fire before the
  generic unknown-key check (`[assignees]`, local `[secrets]`); the removed
  budget keys get the same treatment with a "delete the key" message.

Edits:

1. Delete `src/coga/usage_probe.py` + `tests/test_usage_probe.py`.
2. `src/coga/megalaunch.py`: drop usage_probe import, `probes` param,
   `skipped-budget` outcome, `budget` field on MegalaunchResult, both
   `check_budget` call sites, budget suffix in `render_run_summary`.
3. `src/coga/commands/megalaunch.py`: drop skipped-budget from
   `_drain_post_text`.
4. `src/coga/config.py`: remove the three reserve fields from
   `MegalaunchConfig` + `_parse_megalaunch` + `_ALLOWED_MEGALAUNCH_KEYS`;
   add dedicated ConfigError ("removed with the budget guard — delete the
   key"). Drop `_parse_percent` / `_parse_positive_number` if that leaves
   them unused. Deprecated token-budget keys (`token_guard`,
   `default_token_budget`, `window_hours`, `agent_token_budgets`) are out of
   ticket scope and stay parsed-but-unused.
5. Packaged `coga/cli` SKILL.md: drop "token budget guard" clause and
   `skipped-budget` from the outcome list.
6. `tests/test_megalaunch.py`: delete the 4 budget tests, `_FakeProbe`,
   `_snapshot`, probe monkeypatches, `probes=` args.
7. `tests/test_config.py`: replace reserve-key load test + out-of-range test
   with a "removed key errors with delete-the-key message" test; keep the
   deprecated-token-keys test.

Follow-up candidate (not this ticket): with the guard gone `cfg.megalaunch`
has zero readers — the whole `[megalaunch]` section only parses deprecated
token keys now; could be removed once live configs are clean.

## Implemented (2026-07-15)

Commit `273e2d9b` on `remove-budget-guard` (worktree above), rebased on
current `origin/main`, working tree clean. All plan items landed as written;
notable specifics:

- `MegalaunchResult` lost its `budget` field and `run_megalaunch` its
  `probes` param; `_candidate_result` also dropped its now-unused
  `agent_override` param (its only use was picking the budget window).
- config: removed keys live in a `_REMOVED_MEGALAUNCH_KEYS` frozenset with a
  dedicated pre-check in `_parse_megalaunch` (mirrors the `[assignees]` /
  local-`[secrets]` migration-error precedent): "…removed along with the
  megalaunch budget guard … Delete the key(s)." `_parse_percent` and
  `_parse_positive_number` deleted (reserve keys were their only users).
- tests: 4 budget tests deleted from test_megalaunch.py plus `_FakeProbe`/
  `_snapshot` helpers and probe monkeypatches; test_config.py reserve-key
  load + out-of-range tests replaced by
  `test_megalaunch_removed_reserve_keys_error_with_delete_message`; the
  deprecated-token-keys load test kept.

Verification (scratch venv, python3.12, worktree installed editable):

- `python -m pytest` → 1192 passed, 1 skipped.
- `coga validate --json` in `example/` → ok, no issues.
- Manual repro: a coga.toml with `min_weekly_remaining_percent` fails loud
  with the new delete-the-key message.
- Note: running the suite via bare `PYTHONPATH=src python3.12 -m pytest`
  (no install) fails one pre-existing test
  (`test_bootstrap_script_launch_is_stateless` — spawned script needs an
  installed `coga`); it fails identically on unmodified main and passes
  with the editable install, so it is environmental, not from this change.

## Peer review (2026-07-15)

- Native `codex review --base main`: no must-fix findings. It confirmed the
  budget guard, probe plumbing, outcome/config/test surface, and packaged CLI
  context were removed consistently.
- Confirmed the separate per-session usage path remains intact:
  megalaunch still calls `spawn_agent_session(..., capture_usage=True)`.
- Confirmed `requests` remains a runtime dependency of Slack notification and
  webhook validation code, so keeping it is correct.
- Fetched `origin/main` and rebased unconditionally. The rebased feature commit
  is `c23738cc`; the worktree is clean and exactly one commit ahead of the
  fetched base.
- Post-rebase verification:
  `PYTHONPATH=/home/n/Code/claude/coga-remove-budget-guard/src python -m pytest`
  -> 1192 passed, 1 skipped. A literal uninstalled `python -m pytest` reproduced
  only the documented subprocess import environment failure (1191 passed,
  1 skipped); the absolute source path is the codebase context's prescribed
  sibling-worktree workaround.

## PR

Remove the obsolete megalaunch pre-launch token-budget gate and its per-agent
usage probes. Megalaunch is now an attended, on-demand sweep, so it launches
eligible work without spending a throwaway probe session or silently skipping
agents when vendor usage-window formats drift. Removed reserve config keys now
fail loudly with instructions to delete them, while per-session `## Usage`
capture remains unchanged.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-remove-budget-guard/src python -m pytest` (1192 passed, 1 skipped).
