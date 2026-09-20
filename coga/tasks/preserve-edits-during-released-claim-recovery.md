---
title: Preserve edits during released claim recovery
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
contexts:
- coga/launch-internals
- coga/codebase
- dev/code
---

## Description

Preserve a manual ticket edit made while released-launch recovery fetches control. Reconciliation currently validates one local revision, fetches remotely, then captures a fresh rollback snapshot and overwrites that later revision with the earlier admitted form.

This P2 fix scope comes from [the triage](triage-five-review-comments-that-merged-unanswered.md). The ticket is now activated for implementation.

### Evidence and source

Original [PR 747 comment](https://github.com/FastJVM/coga/pull/747#discussion_r3932656206); source ticket: [megalaunch-activates-picks-before-preflight](megalaunch-activates-picks-before-preflight.md). Assessed 2026-09-18 at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

A real local-Git recovery probe inserted a manual correction during `_control_base_for_attempt`. For both an exact pending remote claim and an already-admitted remote claim, recovery returned success, removed the correction locally, and published without it. Git history shows the helper's relevant body unchanged since PR 747. The Coga publication barrier does not serialize an ordinary editor.

### Expected behavior and scope

Fix `src/coga/commands/launch.py::_reconcile_released_launch_admission` at the boundary between its validated `current_bytes` and the write. Use `git.FileMutationRollback` with the validated revision as its baseline, or compare those exact bytes immediately before writing; do not bless the intervening editor revision by capturing it after fetch.

Keep remote compare-and-set and the pending/admitted distinction intact. On changed local bytes, fail loudly without admitting, publishing, restoring over, or spawning from the stale ticket. Preserve the local released witness and manual correction so an operator can inspect and retry deliberately. This closes the reported fetch window; do not promise a filesystem-wide atomic editor lock.

### Acceptance and focused verification

- Inject a manual body/blackboard edit during the real control fetch, with matching pending control bytes. Reconciliation refuses and preserves the edit and released generation.
- Repeat when control already has the matching admitted revision.
- Confirm unchanged local bytes still allow both existing recovery cases.
- Preserve refusal on mismatched remote bytes, publication-failure recovery and barrier-protected rollback semantics.
- Extend `tests/test_launch.py` next to `test_released_launch_admission_reconciles_control_ticket`; use a local bare remote, no real agent process. Add a focused rollback test only if shared rollback behavior changes.
- Update the released-witness recovery invariant in `coga/contexts/coga/launch-internals/SKILL.md`, the PR 747 gotcha in `coga/codebase`, and their packaged twins; run packaging checks.

Tradeoff: a concurrent manual correction causes a recoverable refusal and another operator retry. That is preferable to silently discarding the correction. Out of scope: changing claim formats, redesigning all launch transactions, or addressing the other already-resolved PR 747 threads.

## Context

- `src/coga/commands/launch.py::_reconcile_released_launch_admission` validates local released bytes, fetches control, and normalizes only an exact matching pending/admitted revision. Its mutation baseline must remain the validated local revision throughout that fetch.
- `src/coga/git.py::FileMutationRollback.require_unchanged` compares live bytes with `originals` before an unarmed mutation; constructing `FileMutationRollback` from validated bytes reuses that guard without changing shared rollback behavior.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/842
branch: fix/released-claim-edits
worktree: /tmp/coga-released-claim-edits

## Implementation plan

- Follow the active `implement` assignment; the earlier draft-only triage sentence predates activation and has been updated to reflect the current ticket state.
- Reproduce the manual-edit fetch window with the local bare-remote fixture for both pending and admitted control revisions, before changing production code.
- Bind the rollback baseline to validated `current_bytes`, retain the existing immediate pre-write check, and preserve remote compare-and-set and barrier-held rollback behavior.
- Update the owning launch-internals invariant and codebase PR 747 gotcha with byte-identical packaged twins; run focused recovery/packaging checks and the complete suite, commit, refresh against main, and bump from the primary checkout.

## Findings and verification

- Confirmed PR 747's original review comment and the unchanged post-fetch snapshot in `commands/launch.py::_reconcile_released_launch_admission`.
- Before the fix, the local bare-remote regression matrix reproduced all four cases (body/blackboard × pending/admitted): launch reported reconciliation success instead of refusing. The two unchanged recoveries, two mismatched-control refusals, and two publication-failure restorations passed (4 failed, 6 passed).
- Use `PYTHONPATH=/tmp/coga-released-claim-edits/src .venv/bin/python -m pytest` from the feature checkout. Its isolated `.venv` has the declared `.[test]` tools, including hatchling so the wheel build is exercised. No shared rollback code change or example-layout/workflow change is needed.
- After the fix, the same focused command passes all 10 cases. The four edit cases exercise the ordinary CLI and assert retry-without-sweep exit 75, the loud changed-input error, exact edited bytes and `released:held-generation`, unchanged local/remote tips, and no agent spawn.
- Updated `coga/launch-internals` as the invariant owner and the PR 747 summary in `coga/codebase`, including both packaged twins. A search of `docs/` found no released-witness specification to reconcile; existing architecture/sync summaries remain accurate. Scope is the control-fetch window, with no atomic editor-lock claim.

Commands run from `/tmp/coga-released-claim-edits`:

- `PYTHONPATH=/tmp/coga-released-claim-edits/src .venv/bin/python -m pytest -q tests/test_launch.py -k 'released_admission_changed_during_control_fetch or released_launch_admission' --tb=short` — red 4/green 10 as above.
- `PYTHONPATH=/tmp/coga-released-claim-edits/src .venv/bin/python -m pytest -q tests/test_packaging.py tests/test_git.py tests/test_megalaunch.py tests/test_launch.py` — 594 passed, including the real wheel build and twin checks.
- `PYTHONPATH=/tmp/coga-released-claim-edits/src .venv/bin/python -m pytest` — 2,665 passed before the final rebase and again on final commit `4d3f65bc` (207.02 seconds).
- `git diff --check` — clean.

## Handoff

- Implementation commit: `4d3f65bc` (`Preserve edits during released claim recovery`). Feature checkout is clean; the feature branch remains unpushed and no PR was opened. Ready for peer review.
- Final `git fetch origin main` brought six generated task/log commits (`3cc80827..becfa9d3`); `git rebase FETCH_HEAD` succeeded without conflicts and `git rev-list --left-right --count origin/main...HEAD` reports `0 1`.
- No adjacent bug was discovered. The existing barrier and conditional rollback are unchanged; a concurrent editor write after the last local comparison remains outside this fix's promised fetch-window scope.

## Peer review

- `codex review --base main` ran from `/tmp/coga-released-claim-edits` and **returned** with no actionable findings. Its own test attempt failed collection because its interpreter lacked `tomlkit`; the complete suite below ran successfully through the prepared feature-checkout environment. Review transcript: `/tmp/coga-released-claim-peer-review.log` (local evidence).
- No must-fix changes or design rethink were needed. Manual inspection confirmed the pre-write guard uses validated bytes and refuses before mutation/rollback; remote pending/admitted handling and the publication barrier remain unchanged. No terminal, pager, TTY prompt, or rendered-message surface changed.
- `git fetch origin main` followed by `git rebase FETCH_HEAD` completed without conflicts onto `b7907dd1`. Final implementation commit: `50c9cfe9`. `git diff 4d3f65bc..HEAD -- src/coga tests` is empty: rebase changed no reviewed source or tests.
- `PYTHONPATH=/tmp/coga-released-claim-edits/src .venv/bin/python -m pytest` — **2,665 passed in 192.17 seconds**, including recovery regressions, packaging/twin checks, and the wheel build.
- `git diff --check` and direct `cmp` checks of both changed live/packaged context pairs passed. Feature checkout is clean, with one implementation commit ahead of fetched main. `git push -u origin fix/released-claim-edits` succeeded at `50c9cfe9`; no PR was opened in this step. This supersedes the earlier unpushed implementation handoff.

## PR

Released-claim recovery could overwrite a manual ticket correction made while it fetched control. Bind its rollback baseline to the exact local bytes validated before that fetch, so an intervening edit causes a retryable refusal while preserving the correction and released witness, without publishing or spawning stale work. An operator must reconcile and retry; this closes the fetch window without claiming an atomic editor lock.

Add local bare-remote coverage for body and blackboard edits against both pending and already-admitted control claims, unchanged recovery, mismatched control, and publication failure. Update the owning launch-internals invariant and codebase summary with matching packaged copies.

Test plan: `PYTHONPATH=/tmp/coga-released-claim-edits/src .venv/bin/python -m pytest` — 2,665 passed; `git diff --check` and both context-pair `cmp` checks passed.
