---
slug: recurring-bugs/recurring-dream-launch-mis-points-coga-task-env-at
title: recurring->dream launch mis-points COGA_TASK_* env at the package template
status: done
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
---

## Description

During `coga recurring --all ~/Code` (2026-07-17), the `xpllm` repo's
`recurring/dream` task launched as an agent, but its injected task-metadata
env vars pointed at the **`bootstrap/recurring-scan` package template**, not
at the real dream task:

```
COGA_TASK_TICKET=.../src/coga/resources/templates/coga/bootstrap/recurring-scan/ticket.md
COGA_TASK_DIR / COGA_TASK_SLUG / COGA_TASK_BLACKBOARD  -> same package template
```

Consequence: when the dream agent ran the `validate-drift` worker script
(which appends its `## Dream Skill: validate-drift` report to
`$COGA_TASK_BLACKBOARD`), the report was written **into the coga package
source tree** at
`src/coga/resources/templates/coga/bootstrap/recurring-scan/ticket.md` in the
`claude/coga` checkout — polluting a shipped template. The dream agent
correctly detected the anomaly, could not revert it (sandbox boundary), and
blocked.

The env vars are being sourced from the outer `bootstrap/recurring-scan`
script launch (the sweep driver) and leaking into the inner agent launch of
`recurring/dream`, instead of being recomputed for the dream task. A nested
launch must re-derive `COGA_TASK_*` from the task it is actually spawning.

**Fix direction:** in the launch path that spawns an agent for a task
(`spawn_agent_session` / the recurring-scan driver), compute the
`COGA_TASK_*` env from the launched task's own ref/dir/blackboard rather than
inheriting whatever the parent process exported. Add a regression test: a
`recurring-scan` script launch that in turn launches an agent task must give
that agent `COGA_TASK_BLACKBOARD` pointing at the task's own `ticket.md`, not
the parent bootstrap template.

## Context

- Env injection for script/agent launches is documented in
  `coga/architecture` ("A script-step launch injects task and skill metadata
  as environment variables"): `COGA_TASK_SLUG`, `COGA_TASK_DIR`,
  `COGA_TASK_TICKET`, `COGA_TASK_BLACKBOARD`, `COGA_TASK_LOG`, etc.
- Shared spawn path: `src/coga/commands/launch.py` `spawn_agent_session(...)`
  and the recurring driver in `src/coga/recurring_runner.py` /
  `bootstrap/recurring-scan/run.py`.
- Secondary hardening: the `validate-drift` worker (and any Dream worker)
  could sanity-check that `$COGA_TASK_BLACKBOARD` is under `coga/tasks/`
  before writing, and refuse to append into a package `resources/templates/`
  path — defense in depth against exactly this mis-point.
- The stray write already landed in `claude/coga`; revert with
  `git -C /home/n/Code/claude/coga checkout -- src/coga/resources/templates/coga/bootstrap/recurring-scan/ticket.md`
  (operational cleanup, not part of the code fix).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
pr: https://github.com/FastJVM/coga/pull/596
branch: fix/dream-task-env
worktree: /tmp/coga-dream-task-env

## Implementation notes

- Preserve unrelated parent environment values, but re-derive the launched
  task's `COGA_TASK_*` metadata at the shared agent-spawn boundary.
- Regression coverage will model an outer bootstrap script environment and
  assert that the inner agent receives the real recurring task paths.
- Root cause confirmed: `run_script_mode` overlays metadata for its own task,
  but `spawn_agent_session` previously forwarded the caller environment
  unchanged, retaining the outer `bootstrap/recurring-scan` values.
- Fix: share the task-metadata builder with agent launches and overlay it at
  the single spawn boundary while preserving unrelated environment entries.
- Kept the live and packaged `coga/architecture` copies aligned with the new
  agent-and-script environment contract.

## Verification

- Regression test before fix: failed with `COGA_TASK_SLUG` equal to
  `bootstrap/recurring-scan` instead of `recurring/dream`.
- Focused suite after fix: `214 passed` (`test_launch.py`,
  `test_launch_script.py`, and `test_recurring.py`).
- Full suite: `1308 passed, 1 skipped` via
  `PYTHONPATH=/tmp/coga-dream-task-env/src python3.12 -m pytest -q`.
- `git diff --check` passes.
- Commit: `f8d0e0b9` (`Re-derive task env for nested agent launches`).
- Final `git fetch origin main && git rebase FETCH_HEAD`: branch already up to
  date; no post-rebase test rerun required.
- Freshness proof: fetched `origin/main` is an ancestor of the branch, which is
  exactly one material commit ahead; feature worktree is clean.
- Task-scoped validation: `ok_count: 1`, no issues.
- Operational cleanup check: the reported package-template path in
  `/home/n/Code/claude/coga` is already clean; no revert remained to perform.

## Peer review

- Native `codex review --base main` completed and found one P2 must-fix: a
  declared secret alias in Coga's own `COGA_*` environment namespace is
  resolved and then silently overwritten by launch metadata.
- Fixed fail-loud by reserving the `COGA_*` namespace for Coga launch
  metadata/control variables, with config and CLI preflight regression
  coverage. Nested agents now also discard outer `COGA_SKILL_*` metadata while
  preserving unrelated parent environment values.
- Focused peer-review suite: `167 passed` (`test_config.py` and
  `test_launch.py`).
- Full suite before rebase: `1310 passed, 1 skipped`.
- Peer-review commit before rebase: `b69c3869`
  (`peer-review: reserve Coga launch environment`).
- Fetched `origin/main` and rebased both feature commits cleanly. Rebased
  commits: `84b302dc` (implementation) and `8ce70bfd` (peer-review fix).
- Full suite after rebase: `1310 passed, 1 skipped` via
  `PYTHONPATH=/tmp/coga-dream-task-env/src python3.12 -m pytest -q`.
- Task-scoped validation after rebase: `ok_count: 1`, no issues.
- Final freshness proof: `origin/main` is an ancestor of the branch, which is
  exactly two commits ahead; feature worktree is clean.
- Operational cleanup rechecked: the package-template path in
  `/home/n/Code/claude/coga` remains clean.

## PR

### Summary

- Re-derive every launched agent's `COGA_TASK_*` paths from the task being
  spawned so nested recurring launches cannot write through the outer
  bootstrap template.
- Preserve unrelated parent environment values, discard stale outer skill
  identity, and fail loud when a ticket secret alias uses Coga's reserved
  `COGA_*` namespace.
- Document the agent-and-script environment contract in both architecture
  copies and add regression coverage for the nested Dream launch and the
  reserved-name preflight.

### Test plan

`PYTHONPATH=$PWD/src python3.12 -m pytest -q` (`1310 passed, 1 skipped`); `PYTHONPATH=$PWD/src python3.12 -m coga.cli validate --task recurring-bugs/recurring-dream-launch-mis-points-coga-task-env-at --json` (`ok_count: 1`, no issues).
