---
slug: recurring-bugs/recurring-all-sweeps-throwaway-coga-scratch-clones
title: recurring --all sweeps throwaway coga scratch clones
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
    skills: []
    assignee: owner
secrets: null
script: null
step: 4 (review)
---

## Description

`coga recurring --all ~/Code` (2026-07-17) discovered 24 coga repos, of which
16 "failed" purely because they are throwaway branch-checkouts of coga itself
that were never meant to be serviced:

- **13× `No user set in coga.local.toml` (exit 2):** `claude/coga-*`,
  `codex/coga-import-llvm-spike`, `codex/magicator-canonical-dynamic-class`,
  `coga-llvm-spike`, etc. Their gitignored `coga.local.toml` has no `user`.
- **3× stale-config migration errors (exit 2):** `[megalaunch]` table
  (`coga-remove-budget-guard`, `coga-usage-to-log`) and `[agents.claude] auto`
  (`patents`).

None of these are real bugs — the fail-loud config guards are working as
designed. The problem is **scope**: `--all` recursively walks every `coga/`
under the path, including a dozen scratch clones/worktrees of the coga repo,
so the useful sweep output is buried under expected failures, and the parent
exits non-zero because of them.

**Fix direction — options to weigh:**
1. **Honor a skip marker:** discovery already skips `_`-prefixed segments
   (per `coga/architecture`); document/lean on that so scratch clones parked
   under a `_`-prefixed dir are excluded. Cheap but requires reorganizing dirs.
2. **Skip un-serviceable repos quietly:** a repo with no `user` set (or a
   config that fails migration) is not a scheduling target — report it once in
   a compact "skipped N unconfigured repos" summary line instead of a full
   error block per repo, and don't let it flip the parent exit code.
3. **Opt-in include list / ignore file:** a `.coga-recurring-ignore` or an
   `--all` config of roots to actually service.

Recommend (2) as the baseline (make expected non-targets quiet and
non-fatal) so `--all` output stays legible, with (1) documented for
intentional exclusion.

## Context

- Discovery: `src/coga/recurring_runner.py` `discover_coga_repos` (prunes on
  first workspace found; already skips dependency/tool trees).
- Parent dispatch + exit code: `run_recurring_all_repos` ("one repo's failure
  does not starve later repos, but the parent exits non-zero after reporting
  the aggregate" — `coga/architecture`).
- Config errors are raised by `load_config` (`src/coga/config.py`) — the
  no-`user` and removed-key migration errors that dominate the failure list.
- Relation to sibling ticket `recurring-all-diverges-two-checkouts-of-one-remote`:
  that one is about correctness when two *serviceable* checkouts share a
  remote; this one is about not attempting the un-serviceable ones at all.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Recovery

The 2026-07-17 megalaunch attempt made no source changes. Its linked-worktree
setup hit the managed sandbox's read-only primary `.git` metadata; the session
then described the limitation conversationally instead of running `coga block`,
so the idle-timeout backstop eventually ended it.

Resume this implement step directly and proceed without another plan-approval
pause. If `git worktree add` cannot write the primary checkout's branch lock,
create an independent `git clone --no-hardlinks` under `/tmp`, repoint `origin`
to the real remote, fetch current `main`, and record that clone as `worktree:`.
If that fallback truly cannot proceed, end with a specific `coga block` call.

Systemic queue/worktree guidance is proposed in
https://github.com/FastJVM/coga/pull/597; this ticket still owns its original
recurring-discovery behavior fix.

## Dev

pr: https://github.com/FastJVM/coga/pull/613
branch: recurring-skip-unconfigured
worktree: /tmp/coga-recurring-skip-unconfigured

## Implementation

- `discover_coga_repos` did not yet prune `_`-prefixed path segments despite
  the ticket's expectation; the branch adds that explicit exclusion alongside
  the existing dependency/tool-tree pruning.
- `run_recurring_all_repos` now preflights discovered workspaces with the full
  `load_config` call. A deliberate `ConfigError` (including missing `user` and
  stale-key migration guards) classifies the checkout as an unconfigured
  non-target: it is not duplicate-grouped or dispatched, is counted in one
  compact summary, and does not affect the parent exit code.
- The classification is deliberately narrow. TOML parse errors, I/O failures,
  unexpected loader bugs, and failures after child dispatch still take the
  existing fail-loud aggregate path; direct single-repo commands are unchanged.
- Updated the live recurring/current-direction/architecture contexts, packaged
  architecture and CLI contexts, and `--all` help text with the same boundary.

## Verification

- Regression-first targeted run failed on both missing behaviors, then passed.
- `python -m pytest tests/test_recurring.py` — 121 passed.
- `PYTHONPATH=/tmp/coga-recurring-skip-unconfigured/src python -m pytest` —
  1323 passed, 1 skipped (the existing optional Hatchling packaging skip).
- `PYTHONPATH=/tmp/coga-recurring-skip-unconfigured/src python -m coga.cli recurring --help`
  — passed.
- `coga validate --task recurring-bugs/recurring-all-sweeps-throwaway-coga-scratch-clones --json`
  — 1 ok, 0 issues.
- A first plain `python -m pytest` run had one fresh-worktree-only child import
  failure (`ModuleNotFoundError: coga`); the documented absolute-`PYTHONPATH`
  invocation above fixed the environment and passed the entire suite.

## Handoff

- Implementation commit after peer-review rebase: `15994b48` (`Skip
  unconfigured repos in recurring all sweeps`).
- Peer-review commit: `46863eaf` (`peer-review: validate aliases before
  recurring sweeps`).
- Freshness: fetched `origin/main` and rebased both feature commits onto
  `5603713a` without conflicts.
- No push or PR was created in this step.

## Follow-up

- Two full-suite runs caused the Dream validate-drift fixture to inherit this
  live launch's task environment and append fixture result blocks to this
  blackboard. The generated blocks were removed. That test-isolation issue is
  unrelated to recurring discovery and was not fixed on this branch.

## Peer Review

- `codex review --base main` found one P2: alias collisions and aliases that
  target unknown commands are intentional config guards, but they run after
  `load_config`, so preflight would still dispatch those repos and fail the
  aggregate sweep.
- Fixed the P2 by moving the existing alias defaults and validator below the
  CLI layer, then using the same merged-default validation in recurring
  preflight. The preflight disables only the duplicate legacy-alias notice;
  malformed TOML and unexpected exceptions remain on the fail-loud child path.
- The review's first plain full-suite run reproduced the already-documented
  fresh-clone child import failure; source-pinned verification remains required.
- `PYTHONPATH=/tmp/coga-recurring-skip-unconfigured/src python -m pytest
  tests/test_aliases.py tests/test_recurring.py` — 145 passed.
- Source-pinned full suite before the rebase — 1323 passed, 1 skipped.
- Clean-environment source-pinned full suite after the rebase — 1323 passed,
  1 skipped.
- Source-pinned task validation — 1 ok, 0 issues.
- Final feature checkout is clean, two commits ahead of fetched `main`, with
  no remaining must-fix findings.

## PR

### Summary

- Make `coga recurring --all` prune `_`-prefixed trees and compactly skip
  workspaces rejected by intentional Coga config guards instead of dispatching
  them as scheduler targets.
- Reuse CLI alias validation during preflight so colliding and unknown-target
  aliases receive the same non-target treatment as missing-user and stale-key
  guards, while parse, I/O, and operational failures remain loud.
- Keep live and packaged behavioral contexts, CLI help, and regression coverage
  aligned with the serviceability boundary.

### Test plan

`PYTHONPATH=/tmp/coga-recurring-skip-unconfigured/src python -m pytest` — 1323 passed, 1 skipped; task-scoped validation — 1 ok, 0 issues.
