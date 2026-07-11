---
slug: fix-open-pr-false-staleness-from-coga-state-commit
title: Fix open-pr false staleness from Coga state commits
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- coga/architecture
- coga/principles
- coga/codebase
- dev/code
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
step: 2 (peer-review)
---

## Description

Stop `code/open-pr` from rejecting a clean feature branch merely because the
control branch advanced through Coga-generated task or audit-log commits after
peer review. The freshness guard should continue when all missing control-branch
changes are confined to non-overlapping `coga/tasks/**` and `coga/log.md` state,
while still failing loud for source, documentation, configuration, mixed, or
overlapping state drift.

Keep `coga validate --check-github` and the script-backed `code/open-pr` step on
the same rule. Surface the accepted state-only drift instead of silently hiding
it, and preserve the existing refusal for materially stale branches.


## Context

The `code/with-review` transition into `open-pr` writes the new ticket step and
audit entries to the control branch. That can make a feature branch fail the
strict `FETCH_HEAD` ancestor check immediately after peer review even when no
product file changed. The current workaround is a repetitive manual rebase.

Relevant contracts: `coga/architecture`, `coga/principles`, `coga/codebase`, and
the packaged `code/open-pr` skill. Update the live and packaged skill copies in
sync.

<!-- coga:blackboard -->

## Production notes

- Root cause reproduced on `docs/init-adopt-existing-repo`: peer review left a
  valid product branch, then task/log sync commits advanced `origin/main` before
  the script step fetched it.
- Intended rule: state-only, non-overlapping drift is safe and visible; any
  material or overlapping drift remains a hard failure.

## Dev

branch: fix/open-pr-state-only-drift
worktree: /tmp/coga-open-pr-state-drift

## Implement

- `github_preflight.check_branch_contains_control` now classifies divergence
  from the merge base. It accepts only changes confined to `coga/tasks/**` and
  `coga/log.md` when the feature branch does not touch the same paths.
- `code/open-pr` consumes that shared result, prints the accepted state-only
  exception, and retains a hard failure for material, mixed, or overlapping
  drift.
- Updated the packaged CLI contract and both live/packaged `code/open-pr`
  skill copies.
- Commits: `6d1489dc` (`Allow open-pr through state-only control drift`) and
  `271120f8` (`Surface accepted state-only branch drift`).
- Verification: focused `tests/test_open_pr.py tests/test_validate.py` -> 61
  passed. After rebasing over current `origin/main`, the full suite produced
  1145 passed, 1 skipped, and the unrelated intermittent
  `test_codex_probe_primes_then_reads_fresh_rollout` failure; its complete
  `tests/test_usage_probe.py` file passes independently (16 passed).
  `git diff --check` is clean. A real probe from the pushed feature worktree,
  while it trails current `origin/main` only by task/log commits, returns
  `ok=True` with `value='state-only-drift'`.
- Relaunch check (2026-07-10): feature worktree clean at `271120f8`, focused
  `tests/test_open_pr.py tests/test_validate.py` re-run -> 61 passed. Step was
  complete but never bumped; bumping now.

## Usage

{"agent":"claude","cache_creation_input_tokens":153065,"cache_read_input_tokens":755742,"cli":"claude","input_tokens":31,"model":"claude-fable-5","output_tokens":7359,"provider":"anthropic","schema":1,"session_id":"b2904d8a-57f3-438c-9079-4d25062900c5","slug":"fix-open-pr-false-staleness-from-coga-state-commit","step":"implement","title":"Fix open-pr false staleness from Coga state commits","ts":"2026-07-11T03:51:25.285230Z","usage_status":"ok"}
