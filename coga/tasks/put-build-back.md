---
slug: put-build-back
title: put-build-back
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (peer-review)
---

## Description

Restore `coga build`, the first-run onboarding flow, which was removed in PR
#691 (`remove-coga-build-and-project`, commit `8394d3b3`, 2026-08-17). Zach
used build on his weather app and it turned a half-baked idea into something
real — it adds value and we want it back. Restore **build only**: `coga
project` and the `bootstrap/project` skill stay removed (explicit owner
decision).

## Context

`coga build` is not a Python command — it is the alias `build = "launch
coga-build"` plus a packaged `coga-build` ticket and the `build/onboarding`
workflow (two agent steps: `gather-and-spec` asks "What do you want to
build?", writes a signed-off vision to `coga/contexts/product/vision/SKILL.md`;
`generate-batch` scaffolds a flat batch of draft tickets from it). The
workflow steps carry no skills; their instructions live inline in the
workflow file. Keep it an alias — per the microkernel rule, a launch-target
command is an argv rewrite in `[aliases]`, not a Typer command.

To restore, revert the build-scoped parts of commit `8394d3b3` (a full
`git revert` would also resurrect `coga project` — don't). That means bringing
back:

- `build` alias in `src/coga/aliases.py` `DEFAULT_ALIASES`, `coga/coga.toml`,
  and `src/coga/resources/templates/coga/coga.toml`
- `coga/workflows/build/onboarding.md` **and** its packaged twin
  `src/coga/resources/templates/coga/workflows/build/onboarding.md` (live and
  packaged copies stay in sync)
- `src/coga/resources/templates/coga/tasks/coga-build.md` (packaged ticket)
- the reverted `src/coga/commands/init.py` seeding and the associated test
  coverage removed from `tests/test_aliases.py`, `tests/test_init.py`,
  `tests/test_packaging.py`
- the two `coga build` → `coga chat` `purpose` strings in
  `src/coga/dependencies.py`, and the seeded `[coga-build] created` line in
  `src/coga/resources/templates/coga/log.md`
- doc/context mentions trimmed by the PR (README, `docs/getting-started.md`,
  `docs/reference.md`, `docs/cli-extension-audit.md`,
  `coga/contexts/coga/architecture`, `coga/contexts/coga/codebase`,
  `coga/contexts/coga/usage`, packaged `bootstrap/contexts/coga/cli` and
  `bootstrap/contexts/coga/architecture`) — restore only the build mentions,
  leave `project` mentions out, and resolve any drift from commits landed
  since the removal. Drift is nontrivial (`src/coga/aliases.py` and the
  packaged `coga.toml` have both changed since); where reverted text
  conflicts with current text, current text wins — re-add the build mentions
  on top of it rather than restoring old prose wholesale.

Leave removed: `src/coga/commands/project.py`, the `bootstrap/project` skill,
`tests/test_project.py`, and the packaged `bootstrap/project/ticket.md`.

Evaluator notes (2026-08-18): restore the old empty-repo-only seeding
semantics as-is — that design is still wanted, not just the old code. When
restoring the packaged `coga-build` ticket template, check its frontmatter
against current template conventions (several `recurring/` templates were
reworked after the removal).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: restore-coga-build
worktree: /home/n/Code/codex/coga-put-build-back

## Implement notes (2026-08-18)

Committed `996e8c77` "Restore coga build first-run onboarding" — the
build-scoped revert of `8394d3b3`, with `coga project` left removed.

What was restored verbatim (verified byte-identical to `8394d3b3^`):
`src/coga/commands/init.py` (empty-repo-only seeding, `_prune_onboarding_tickets`,
`_stamp_user_into_delivered_tickets`, next-step coax), `src/coga/dependencies.py`
purpose strings, README quickstart, packaged `log.md` seed line, both
`workflows/build/onboarding.md` twins (identical to each other), and the
`codebase` context alias example.

Deliberate deviations from a plain revert:

- Packaged `tasks/coga-build.md` gains `secrets: null` (current `_template`
  convention; `secrets` is in `OPTIONAL_TASK_KEYS` so old form was valid too).
- Drifted files got build re-added on top of current text, not old prose:
  `aliases.py` (build after dream in `DEFAULT_ALIASES` + comment sentence),
  `docs/cli-extension-audit.md` (kept "registered recipes", re-added the
  `build` task mention and the eight-alias counts), `usage` context (kept
  "other bootstrap launches", added onboarding (`coga build`) mention).
- `tests/test_packaging.py` gains an `IDENTICAL_LIVE_PACKAGED_PAIRS` entry for
  `workflows/build/onboarding.md` — enforces the ticket's "live and packaged
  copies stay in sync" requirement (removal PR had only removed the project
  line there).
- `tests/test_init.py` fake-seeder loop keeps project out
  (`("orient", "ticket")`); everything else restored, including the vestigial
  dir-form fake coga-build template (init tests copy the REAL packaged tree —
  `init.py` imports `packaged_template_root` directly, so the `fake_vendor`
  monkeypatch on `update_cmd` doesn't redirect it; pre-existing quirk kept).
- `tests/test_aliases.py` parametrize restored to `["status", "build"]`.

Left untouched on purpose: `coga project` surfaces (command, skill, tests,
packaged ticket, doc/context mentions), the project-only hunks in both
`architecture` contexts and `cli.py`, and the historical task-note edits under
`coga/tasks/cleanup-core-commands/` (ticket didn't list them).

Tests: `python3.12 -m pytest` in the worktree — 1799 passed, 1 skipped,
3 failed. All 3 failures are PRE-EXISTING on clean origin/main (verified by
running them in the pristine primary checkout): adjacent bug, not mine.

## Adjacent bug (follow-up ticket candidate)

`tests/conftest.py:121` (autouse fixture) deletes `SLACK_WEBHOOK_URL` with
`raising=False`; three tests then call `monkeypatch.delenv("SLACK_WEBHOOK_URL")`
with default `raising=True` and hit a deterministic KeyError regardless of
environment: `test_autoclose.py::test_recipe_preflights_live_summary_before_closing`
(line 751), `test_recurring.py::test_named_launch_keeps_control_only_malformed_ledger_blocked_on_retry`,
`test_recurring.py::test_sweep_retry_revalidates_control_only_malformed_ledger`.
Fix is `raising=False` (or drop the redundant delenv). Not fixed here — out of
ticket scope.
