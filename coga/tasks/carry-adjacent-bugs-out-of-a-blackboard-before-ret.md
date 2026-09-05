---
slug: carry-adjacent-bugs-out-of-a-blackboard-before-ret
title: Carry adjacent bugs out of a blackboard before Retro deletes it
status: in_progress
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 3 (open-pr)
---

## Description

`coga/skills/code/implement/SKILL.md` instructs: "If you find a real adjacent bug, write it on the
blackboard for a follow-up ticket; don't fix it here." Nothing downstream is required to carry that
note out. Dream Phase 4 then deletes done tickets — with their blackboards — so an adjacent bug
parked this way is destroyed unless a human happened to read it first.

Either `code/implement` must require filing the follow-up ticket before bump, or
`retro/done-ticket` must treat parked adjacent bugs as durable knowledge. Decide which.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-11), classified `gap`. Verified live in
this repo.

Directly relevant to Dream itself: this run's Phase 4 deleted 8 done tickets. The risk is not
hypothetical.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/757
branch: retro-adjacent-bugs
worktree: /tmp/coga-retro-adjacent-bugs

## Implement plan

- Make `retro/done-ticket` responsible for carrying unresolved adjacent bugs
  into durable contexts before deleting their source tickets. Retro is already
  the knowledge-extraction gate; this also protects notes parked before this
  change, whereas filing only during implement would protect future notes.
- Preserve the symptom, affected area, evidence/reproduction, and unresolved
  follow-up status as a known failure mode in the same reviewable knowledge PR
  as the deletion. Distinguish actionable unresolved bugs from execution noise;
  keep duplicate findings covered by an existing durable context deduplicated.
- Clarify the implement-to-Retro handoff in both implement skill copies and
  document the contract in the relevant context. Retro has no live skill
  override under `coga/skills/`; its source is the packaged bootstrap skill.
- Run the existing template checks and full pytest suite, commit the feature
  branch, freshen it from `origin/main`, and bump from this primary checkout.

## Implementation

- Updated the packaged Retro skill to require scanning the whole blackboard
  for unresolved adjacent bugs before choosing direct deletion. Uncovered bugs
  are durable known failure modes; their actionable evidence and unresolved
  status move into a context in the same PR as the source deletion.
- A source/attachment/follow-up link alone is insufficient. Evidence must be
  understandable after the source disappears. Existing corpus coverage and
  the running delta still deduplicate; a delta-covered bug retains at least
  one source until its knowledge PR lands.
- Updated both live and packaged implement skills to record the symptom,
  affected code, reproduction/evidence, and unresolved status. Both architecture
  contexts now assign preservation to Retro. No Python or workflow/layout
  changes, and no seeded example changes are needed.

## Verification

- Baseline Retro template checks passed (3 tests).
- `PYTHONPATH=/tmp/coga-retro-adjacent-bugs/src python -m pytest`:
  2368 passed, 2 failed. One failure was missing `hatchling` in the default
  interpreter; installing the declared `.[test]` dependencies in the isolated
  `/tmp/coga-retro-adjacent-bugs-test-venv` resolved it. The wheel test then
  passed. The remaining failure is the pre-existing fixture bug below.
- After rebasing, ran:

  ```sh
  PYTHONPATH=/tmp/coga-retro-adjacent-bugs/src /tmp/coga-retro-adjacent-bugs-test-venv/bin/python -m pytest tests/test_code_implement_skill.py tests/test_retro_skill_template.py tests/test_dream_worker_templates.py tests/test_packaging.py -q
  ```

  All 22 passed. Incoming `main` commits changed only task state and the audit
  log, so the full-suite source/test baseline is unchanged.
- `coga validate --task carry-adjacent-bugs-out-of-a-blackboard-before-ret --json`
  with primary-checkout source: one valid task, no issues.
- `git diff origin/main...HEAD --check` passed; both edited live/package pairs
  remain byte-identical. `git merge-base --is-ancestor origin/main HEAD` passed.

## Adjacent bug — recurring notification test fixture

- `tests/test_notification_messages.py::test_recurring_create_is_silent`
  creates a directory with `force_directory=True` but constructs its `TaskRef`
  with `file_form=True`. `_broadcast_scan` acquires a period lease, which reads
  the directory as a file and raises `IsADirectoryError` instead of reaching
  the notification assertion. This is unrelated to the Markdown changes here.
- Reproduced on primary `main`, using its unchanged source and test:

  ```sh
  PYTHONPATH=/home/n/Code/codex/coga/src python -m pytest tests/test_notification_messages.py::test_recurring_create_is_silent -q
  ```

  Result: the same `IsADirectoryError` at `src/coga/recurring.py:85` from
  `src/coga/recurring_runner.py:4694`; fixture construction is at
  `tests/test_notification_messages.py:394`.
- The same test has an earlier failure note on
  `coga/tasks/dream-reconciliation-must-count-distinct-shard-ids.md` (then
  `NotADirectoryError`). No dedicated follow-up identified; fixture correction
  remains unresolved and was not included in this change.

## Handoff

- Commit: `a1d6ecab` — Preserve adjacent bugs before Retro deletes tickets.
- Clean feature worktree, rebased on fetched `origin/main` at `69366677`.
- No feature push or PR. The attending human explicitly approved advancing to
  peer-review with the known baseline test failure documented. The unrelated
  fixture bug remains unresolved; the implementation and its relevant checks
  are ready for handoff.

## Peer review

- `codex review --base main` completed with no actionable regressions. No
  must-fix findings or design changes were needed. The reviewer's default
  interpreter passed 21 focused tests and hit the already-documented missing
  `hatchling` dependency in the wheel test.
- Fetched `origin/main` and rebased the feature branch onto `03a4d0a2`; no
  conflicts. The feature commit is now `f246e6ea`. `git range-diff
  a1d6ecab^..a1d6ecab f246e6ea^..f246e6ea` confirms the reviewed patch is
  unchanged. Incoming commits changed only task state and the audit log.
- `git diff origin/main...HEAD --check` and
  `git merge-base --is-ancestor origin/main HEAD` passed. Both edited
  live/package pairs remain byte-identical (`cmp`). The feature worktree is
  clean with one commit ahead of `origin/main`.
- Primary-checkout task validation passed: one valid task, no issues:

  ```sh
  PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-retro-adjacent-bugs-test-venv/bin/python -m coga.cli validate --task carry-adjacent-bugs-out-of-a-blackboard-before-ret --json
  ```
- Full post-rebase suite completed with the prepared test environment:

  ```sh
  PYTHONPATH=/tmp/coga-retro-adjacent-bugs/src /tmp/coga-retro-adjacent-bugs-test-venv/bin/python -m pytest
  ```

  Result: **2369 passed, 1 failed** in 169.42 seconds. The only failure is
  `tests/test_notification_messages.py::test_recurring_create_is_silent`,
  with the same `IsADirectoryError` documented above; the packaging test now
  passes. No additional failure or unresolved review finding.
- Ready for the mechanical `open-pr` step: clean recorded feature worktree,
  reviewed commit `f246e6ea`, fresh base `03a4d0a2`, and PR body below. The
  existing approval to proceed with the documented baseline fixture failure
  still applies. No feature push or PR in this step.

## PR

Completed tickets can contain unresolved adjacent bugs that disappear when
Retro deletes their blackboards. Make `retro/done-ticket` preserve each
uncovered bug's symptom, affected area, evidence or reproduction, and unresolved
follow-up in a fitting context in the same reviewable PR as the source deletion.
Deduplication against this run's pending knowledge keeps at least one source
carrying the evidence until that PR lands.

Update both implement skill copies to record an actionable handoff and both
architecture contexts to assign preservation to Retro. This protects existing
parked findings as well as future ones; fixing those bugs remains follow-up
work. The change is limited to Markdown skills and contexts.

Test plan: `PYTHONPATH=/tmp/coga-retro-adjacent-bugs/src /tmp/coga-retro-adjacent-bugs-test-venv/bin/python -m pytest` — 2369 passed; the sole failure is the pre-existing `test_recurring_create_is_silent` directory/file fixture mismatch (`IsADirectoryError`). `codex review --base main` found no actionable regressions; task validation, `git diff origin/main...HEAD --check`, and live/package parity checks passed.
