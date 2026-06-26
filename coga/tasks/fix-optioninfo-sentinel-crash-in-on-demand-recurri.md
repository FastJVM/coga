---
slug: fix-optioninfo-sentinel-crash-in-on-demand-recurri
title: Fix OptionInfo sentinel crash in on-demand recurring launchers
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: optioninfo-timeouts
worktree: /tmp/relay-optioninfo-timeouts
pr: https://github.com/FastJVM/relay/pull/436

- 2026-06-24: open-pr step — branch pushed (2 commits ahead of origin/main), PR #436 opened against main. `gh pr checks 436` reports no CI checks configured on the repo, so there is no CI gate to be green on.

## Implementation notes

- 2026-06-24: Confirmed the scan's approximate line numbers are stale in current source: `_launch_created` is around `src/relay/commands/recurring.py:314`; the supervisor comparison still lives in `src/relay/repl_supervisor.py` and still requires `float | None` values, not Typer `OptionInfo` sentinels.
- Plan: reuse `_recurring_idle_timeout(load_config())` / `_recurring_max_session(load_config())` for on-demand `relay recurring launch <name>` when not `--interactive`, mirroring the scheduled sweep. Add a regression beside the existing `recurring launch` tests.
- Implemented in `/tmp/relay-optioninfo-timeouts`: `_launch_created` now receives the already-loaded config and passes concrete `idle_timeout` / `max_session` values into the in-process `relay launch` call. `--interactive` still leaves both limits unarmed. Updated `relay/recurring` context with that behavior note.

## Peer review

- 2026-06-24: Native `codex review --base beca1a04d980d93ba00b2b3387b863c0fbfb87ac` found one must-fix: the runtime path was fixed, but the shipped bootstrap `relay/cli` context still described the timeout backstop as only applying to bare/`--all` recurring sweeps.
- Fixed in `/tmp/relay-optioninfo-timeouts` commit `9d38df3` by syncing `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/cli/SKILL.md` with the on-demand `recurring launch <name>` timeout contract.

## Verification

- `/tmp/relay-optioninfo-timeouts`: `python -m pytest tests/test_recurring.py -q` -> 82 passed.
- `/tmp/relay-optioninfo-timeouts`: `python -m pytest` -> 884 passed, 1 skipped.
- `/tmp/relay-optioninfo-timeouts`: `git diff --check` -> clean.
- `/tmp/relay-optioninfo-timeouts`: `codex review --base beca1a04d980d93ba00b2b3387b863c0fbfb87ac` -> one P2 packaged-context sync finding; fixed in `9d38df3`.
- `/tmp/relay-optioninfo-timeouts`: post-review `git diff --check` -> clean.
- `/tmp/relay-optioninfo-timeouts`: post-review `python -m pytest tests/test_recurring.py -q` -> 82 passed.
- `/tmp/relay-optioninfo-timeouts`: post-review `python -m pytest` -> 884 passed, 1 skipped.
- `/home/n/Code/codex/relay`: post-review `PYTHONPATH=/tmp/relay-optioninfo-timeouts/src python -m relay.cli validate --task fix-optioninfo-sentinel-crash-in-on-demand-recurri --json` -> ok_count 1, no issues.
- `/tmp/relay-optioninfo-timeouts`: `python -m relay.cli validate --task fix-optioninfo-sentinel-crash-in-on-demand-recurri --json` could not run because the feature worktree lacks `relay-os/relay.local.toml user`.
- `/home/n/Code/codex/relay`: `PYTHONPATH=/tmp/relay-optioninfo-timeouts/src python -m relay.cli validate --task fix-optioninfo-sentinel-crash-in-on-demand-recurri --json` -> ok_count 1, no issues.
- `/home/n/Code/codex/relay`: `PYTHONPATH=/tmp/relay-optioninfo-timeouts/src python -m relay.cli validate --task fix-optioninfo-sentinel-crash-in-on-demand-recurri --json` after lifecycle recovery -> ok_count 1, no issues.

## Owner review assist

- 2026-06-24: Codex review-gate check found PR #436 open and ready for owner review; local `optioninfo-timeouts` is clean at `9d38df3` and matches `origin/optioninfo-timeouts`. `origin/main...HEAD` is `6 2`, but the newer `main` commits only touch Relay task-state/log files; merge simulation reports no conflicts.
- Fresh verification: `git diff --check origin/main...HEAD` clean; `gh pr checks 436` reports no checks; `/tmp/relay-optioninfo-timeouts` `python -m pytest tests/test_recurring.py -q` -> 82 passed; `/tmp/relay-optioninfo-timeouts` `python -m pytest -q` -> 884 passed, 1 skipped; primary checkout `PYTHONPATH=/tmp/relay-optioninfo-timeouts/src python -m relay.cli validate --task fix-optioninfo-sentinel-crash-in-on-demand-recurri --json` -> ok_count 1, no issues.
- Recommendation: code/docs/tests look ready to merge. Do not advance or close the task here; owner merge/autoclose should handle the review gate.

## Blocker

- 2026-06-24: Implementation is committed on `optioninfo-timeouts` (`94a938d`), but `relay bump fix-optioninfo-sentinel-crash-in-on-demand-recurri` refused with `Task fix-optioninfo-sentinel-crash-in-on-demand-recurri is 'draft'. Cannot advance.` The composed prompt assigned the current step as `implement`, but the ticket frontmatter still has `status: draft`; CLI-owned status should not be hand-edited.
- 2026-06-24: Live ticket state is now `status: in_progress`, `step: 1 (implement)`, so the draft-status blocker has been cleared through the CLI lifecycle path. Retrying the implement handoff from the primary checkout.

---

## Blockers

- [2026-06-24 15:11] [agent:claude] Implementation commit 94a938d is complete, but relay bump cannot advance because the ticket frontmatter is still status: draft while the launch prompt assigned step 1 (implement).

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":144640,"cli":"codex","input_tokens":76040,"model":"gpt-5.5","output_tokens":4103,"provider":"openai","schema":1,"session_id":"019efbb0-c7e9-7701-a9ac-5b3d91e745c2","slug":"fix-optioninfo-sentinel-crash-in-on-demand-recurri","step":"implement","title":"Fix OptionInfo sentinel crash in on-demand recurring launchers","ts":"2026-06-24T22:13:38.529272Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":1717632,"cli":"codex","input_tokens":90947,"model":"gpt-5.5","output_tokens":7927,"provider":"openai","schema":1,"session_id":"019efbb2-2d46-7452-b1d2-33db51e334e1","slug":"fix-optioninfo-sentinel-crash-in-on-demand-recurri","step":"peer-review","title":"Fix OptionInfo sentinel crash in on-demand recurring launchers","ts":"2026-06-24T22:23:12.011338Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":73612,"cache_read_input_tokens":790797,"cli":"claude","input_tokens":16285,"model":"claude-opus-4-8","output_tokens":16429,"provider":"anthropic","schema":1,"session_id":"77bd2f96-d3ee-4cf3-8921-e7542dbe6b17","slug":"fix-optioninfo-sentinel-crash-in-on-demand-recurri","step":"open-pr","title":"Fix OptionInfo sentinel crash in on-demand recurring launchers","ts":"2026-06-24T22:25:00.879924Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":470528,"cli":"codex","input_tokens":55323,"model":"gpt-5.5","output_tokens":8117,"provider":"openai","schema":1,"session_id":"019efbbf-9527-7012-b80b-12f16c0dd3b5","slug":"fix-optioninfo-sentinel-crash-in-on-demand-recurri","step":"review","title":"Fix OptionInfo sentinel crash in on-demand recurring launchers","ts":"2026-06-24T22:46:45.089547Z","usage_status":"ok"}
