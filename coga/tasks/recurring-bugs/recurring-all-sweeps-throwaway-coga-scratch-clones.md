---
slug: recurring-bugs/recurring-all-sweeps-throwaway-coga-scratch-clones
title: recurring --all sweeps throwaway coga scratch clones
status: active
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
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
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
