---
slug: fix-optioninfo-sentinel-crash-in-on-demand-recurri
title: Fix OptionInfo sentinel crash in on-demand recurring launchers
status: in_progress
autonomy: interactive
owner: nick
human: nick
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
step: 1 (implement)
---

## Description

Found by the Dream run on 2026-06-18 (knowledge scan, gap finding G-NEW-2).
Reproduced in the `marketing/relay-build-command` blackboard but never filed.

`recurring._launch_created` (`src/relay/commands/recurring.py`, ~line 498) omits
`idle_timeout`/`max_session` when launching, so those arrive as Typer
`OptionInfo` sentinel objects. `repl_supervisor` (`src/relay/repl_supervisor.py`,
~line 286) then evaluates `float >= OptionInfo` → `TypeError`, crashing the
**on-demand** TTY launchers: `relay dream` (= `relay recurring launch dream`)
and `relay recurring launch <x>`.

The scheduled bare `relay recurring` sweep sets the timeouts explicitly, so only
the on-demand paths break. This directly threatens the `relay dream` entry point
that Dream itself documents.

Fix direction: pass concrete `idle_timeout`/`max_session` defaults (or resolve
the sentinels) in `_launch_created` so on-demand launches match the swept path.
Confirm the exact line numbers/signature before implementing — they were
reported by a scan, not yet verified against current source.

## Context

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: optioninfo-timeouts
worktree: /tmp/relay-optioninfo-timeouts

## Implementation notes

- 2026-06-24: Confirmed the scan's approximate line numbers are stale in current source: `_launch_created` is around `src/relay/commands/recurring.py:314`; the supervisor comparison still lives in `src/relay/repl_supervisor.py` and still requires `float | None` values, not Typer `OptionInfo` sentinels.
- Plan: reuse `_recurring_idle_timeout(load_config())` / `_recurring_max_session(load_config())` for on-demand `relay recurring launch <name>` when not `--interactive`, mirroring the scheduled sweep. Add a regression beside the existing `recurring launch` tests.
- Implemented in `/tmp/relay-optioninfo-timeouts`: `_launch_created` now receives the already-loaded config and passes concrete `idle_timeout` / `max_session` values into the in-process `relay launch` call. `--interactive` still leaves both limits unarmed. Updated `relay/recurring` context with that behavior note.

## Verification

- `/tmp/relay-optioninfo-timeouts`: `python -m pytest tests/test_recurring.py -q` -> 82 passed.
- `/tmp/relay-optioninfo-timeouts`: `python -m pytest` -> 884 passed, 1 skipped.
- `/tmp/relay-optioninfo-timeouts`: `git diff --check` -> clean.
- `/tmp/relay-optioninfo-timeouts`: `python -m relay.cli validate --task fix-optioninfo-sentinel-crash-in-on-demand-recurri --json` could not run because the feature worktree lacks `relay-os/relay.local.toml user`.
- `/home/n/Code/codex/relay`: `PYTHONPATH=/tmp/relay-optioninfo-timeouts/src python -m relay.cli validate --task fix-optioninfo-sentinel-crash-in-on-demand-recurri --json` -> ok_count 1, no issues.

## Blocker

- 2026-06-24: Implementation is committed on `optioninfo-timeouts` (`94a938d`), but `relay bump fix-optioninfo-sentinel-crash-in-on-demand-recurri` refused with `Task fix-optioninfo-sentinel-crash-in-on-demand-recurri is 'draft'. Cannot advance.` The composed prompt assigned the current step as `implement`, but the ticket frontmatter still has `status: draft`; CLI-owned status should not be hand-edited.

---

## Blockers

- [2026-06-24 15:11] [agent:claude] Implementation commit 94a938d is complete, but relay bump cannot advance because the ticket frontmatter is still status: draft while the launch prompt assigned step 1 (implement).
