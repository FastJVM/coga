---
slug: recurring-bugs/dream-recipes-write-reports-into-packaged-bootstra
title: Dream recipes write reports into packaged bootstrap tickets
status: done
owner: nicktoper
human: nicktoper
agent: codex
assignee: nicktoper
contexts:
- coga/architecture
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
---

## Description

A Dream worker recipe invoked from inside a **stateless bootstrap session**
appends its `## Dream Skill: <name>` run report into the *packaged* bootstrap
`ticket.md` — a shipped package resource under `src/coga/resources/templates/`
— instead of a task blackboard. Observed 2026-07-27: two `validate-drift`
reports were appended to
`src/coga/resources/templates/coga/bootstrap/orient/ticket.md` during a
`bootstrap/orient` chat session, leaving the working tree dirty with edits to a
file that ships in the wheel. Reverted by hand at `4bb4885e`; nothing was
committed.

Done when a recipe run under a stateless bootstrap target writes its report to
stdout (the existing no-blackboard path) and leaves every packaged resource
untouched, with a regression test that fails on the current code.

## Context

**Root cause.** `task_env.build_task_env` sets `COGA_TASK_BLACKBOARD` to the
launched task's resolved `ticket_path` (`src/coga/task_env.py:32`). For a
bootstrap target with no repo-local override, that path resolves to the
**packaged** resource. Every Dream worker recipe then reads the variable and
appends to whatever it names:

- `src/coga/dream_validate_drift.py:520` (`script_blackboard_from_env`) →
  `append_report(blackboard, report)` at ~:600
- `src/coga/dream_cleanup_orphan_markers.py:67`
- `src/coga/skill_update.py:212`

All three already have the correct fallback one branch away — when no
blackboard is resolved they `sys.stdout.write(report)`. The bug is that they
are handed a path they should never receive.

**Where the boundary belongs.** `coga/architecture` states bootstrap tickets
are stateless: "no status, no workflow" and "no status, no owner, no log, no
lock". A stateless target has no blackboard, so `build_task_env` should not
emit `COGA_TASK_BLACKBOARD` for one. Fixing it there fixes all three recipes at
once and matches the existing contract, rather than adding a guard to each
writer. Consider whether the writers should *also* refuse a path outside
`coga/tasks/` — defense in depth against the same class, and cheap.

**Scope note.** The packaged `bootstrap/orient/ticket.md` is the observed
victim, but nothing is orient-specific: any `coga run <recipe>` invoked from
any bootstrap session hits it, and a repo with a local
`coga/bootstrap/<name>/ticket.md` override would get that file corrupted
instead.

**Two loose ends found while diagnosing — investigate, don't assume.**

1. The reports are byte-identical and were appended **twice**, four minutes
   apart. Each recipe's known-skill contract declares an `Idempotency` rule;
   check whether `append_report` is meant to dedupe a same-content section and
   isn't, or whether two reports is correct behavior for two runs.
2. Both reports record the applied fix
   `` `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`) ``. There is
   no task `x` on disk now, and `validate.py:361` carries the comment that the
   log is repo-global `coga/log.md`, "not a per-task file". So `--fix` may be
   creating per-task `log.md` files that the current model says should not
   exist. That is a separate defect if confirmed — split it into its own ticket
   rather than widening this one.

**This class was closed once already — read that fix first.** PR #596
("recurring->dream launch mis-points COGA_TASK_* env at the package template",
merged 2026-07-18, ticket since retired) fixed the *nested launch* path by
re-deriving `COGA_TASK_*` from the task being spawned, "so nested recurring
launches cannot write through the outer bootstrap template" — the identical
symptom. It touched `commands/launch.py`, `commands/launch_script.py`,
`delete_task.py`, and both architecture copies, with regression tests in
`tests/test_launch.py`. Start there; the boundary that fix established is the
one to extend.

What #596 did **not** cover is recipe invocation, because `coga run` inherits
by design. `coga/architecture` states it explicitly: "An agent invoking a
recipe keeps its inherited `COGA_TASK_*`; the recurring runner explicitly
re-derives that metadata for the instantiated period task." Inheritance is
correct for an ordinary task; it is wrong when the outer task is a stateless
bootstrap target, because there the inherited ticket path *is* a packaged
resource. So the likely shape of the fix is: keep recipe inheritance, but never
hand a stateless bootstrap target a `COGA_TASK_BLACKBOARD` in the first place.

**Establish the actual invocation path before fixing — the timeline does not
line up with the obvious story.** The two reports are stamped 17:03 and 17:07
UTC; `coga run` only merged to main at 17:22 UTC that same day (PR #650). So
these were *not* produced by the merged `coga run`. Determine what actually
ran — a feature branch or worktree carrying #650, or the older `script: run.py`
seam reaching the same recipe module — because it decides whether this is a gap
in the new surface or a live hole in the seam that
`remove-run-py/delete-the-script-seam` will remove anyway.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/671
branch: fix/stateless-bootstrap-blackboard
worktree: /tmp/coga-stateless-bootstrap-blackboard

## Investigation

- PR #596 (`267455c4`) established that every nested launch re-derives
  `COGA_TASK_*` at the shared spawn boundary. The remaining hole is the
  environment initially built for a `BootstrapRef`: recipes correctly inherit
  it, but a stateless bootstrap definition should never receive a mutable
  blackboard path.
- The observed 17:03/17:07 UTC writes happened inside the `bootstrap/orient`
  session launched at 16:14 UTC to resolve PR #650. PR #650's final feature
  commit (`e75ca28a`) was not created until 17:20 UTC and merged at 17:22 UTC,
  so the new `coga run` path was live in its feature worktree during testing
  even though it was not yet on `main`.
- **Correction (2026-07-29, recovered from the stale checkout's parallel
  blackboard before dropping its stash).** The invocation path was *not*
  `coga run` at all. The parallel diagnosis reproduced the pollution live in
  the primary checkout: a report stamped `2026-07-28T03:53:16+00:00` with
  ``Task: `bootstrap/orient` `` and the same fixture payload, written by
  **pytest running the recipe in-process** inside a `bootstrap/orient` session
  and inheriting that session's `COGA_TASK_BLACKBOARD`. That is why the stamps
  predate `coga run` merging at 17:22 — neither a gap in the new `coga run`
  surface nor a hole in the since-deleted `script: run.py` seam. It does not
  narrow this ticket (the env boundary is still the durable fix: a bootstrap
  target that exports no blackboard stops recipe, test, and future writers at
  once), and the test-harness half is owned by
  `scrub-coga-task-in-the-pytest-autouse-guard-so-fix` (PR #673).
- The duplicate reports represent two executions. `append_report` is
  intentionally append-only; the known-skill Idempotency clause promises that
  safe repairs converge, not that distinct run reports are deduplicated.
- The reported ``x/log.md`` repair is mocked fixture data in
  `tests/test_dream_validate_drift.py`, not evidence that current
  `coga validate --fix` created a real per-task log. The current safe-fix path
  only restores a missing blackboard fence/region, so no follow-up defect was
  confirmed.

## Implementation

- `build_task_env` now omits `COGA_TASK_BLACKBOARD` for `BootstrapRef` while
  retaining the ordinary task contract.
- Both agent and script spawn boundaries remove any inherited
  `COGA_TASK_BLACKBOARD` before overlaying the target's freshly built
  metadata, so a nested stateless launch cannot retain an outer task's path.
- Added an agent/recipe regression that runs registered `validate-drift` from
  the captured bootstrap environment and proves the report goes to stdout
  while a package-shaped `bootstrap/orient/ticket.md` stays byte-identical.
  Added the corresponding inherited-env assertion for stateless bootstrap
  scripts.
- Kept policy at the launch metadata boundary instead of adding three
  writer-side path guards. Updated both live and packaged `coga/architecture`
  copies with the stateless exception.

## Verification

- Before the fix:
  `tests/test_launch.py::test_stateless_bootstrap_recipe_reports_to_stdout_without_mutating_ticket`
  failed because the report was appended to the package-shaped ticket.
- Focused regression set: `294 passed`.
- Full suite: `1577 passed, 1 skipped`.
- Scoped validation:
  `coga validate --task recurring-bugs/dream-recipes-write-reports-into-packaged-bootstra --json`
  reported one clean task and no issues.
- Committed as `b08130e7` (`Keep stateless bootstrap reports off ticket
  definitions`).
- Fetched `origin/main` and rebased onto `FETCH_HEAD`; the branch was already
  current at `0f0df256`.

## Peer review

Reviewed by Claude (the non-authoring agent). `/code-review` is
user-invocable only in this harness, so it could not be launched from the
session; the diff is ~100 lines across 6 non-test files, so the review was
done directly rather than blocking the queue on a tool restriction.

Verified rather than assumed:

- **Both regression tests genuinely fail on pre-fix code.** Reverted
  `task_env.py` to the unconditional assignment and reran: the agent/recipe
  test fails, and the script test fails showing
  `blackboard=<repo>/coga/bootstrap/probe/ticket.md` — so it also covers the
  ticket's scope note that a repo-local `coga/bootstrap/<name>/` override
  would be the corrupted file. Fix restored, both pass.
- **No legitimate consumer breaks.** All three writers
  (`dream_validate_drift.py:520`, `skill_update.py:212`,
  `dream_cleanup_orphan_markers.py:67`) return `None` on an unset variable
  and fall through to the existing stdout path. No bootstrap `ticket.md`
  references the variable in prose or script.
- **The third `build_task_env` caller is safe.** `recurring_runner.py:590`
  needs no pop: its ref is always a period `TaskRef`, so the re-derived value
  overwrites any inherited one.
- **`spawn_agent_session` copies before popping** (`env = dict(env)`), so
  caller-owned environments are unmutated.

Findings applied (commit `37f5ac52`):

1. In `run_script_mode` the new `env.pop` had been inserted *between* the
   secrets comment and the `build_task_env` line that comment documents, so
   the comment read as if it explained the pop. Gave the pop its own comment
   and restored adjacency.
2. The packaged `coga/cli` context still listed `COGA_TASK_BLACKBOARD` as an
   unconditional script-launch variable, which this change makes false for
   stateless targets. Corrected. (Packaged-only — there is no live
   `coga/contexts/coga/cli/`, so nothing to sync.)

Deliberately not changed:

- `isinstance(ref, BootstrapRef)` is a negative type test; a positive
  `isinstance(ref, TaskRef)` would fail safe if a third stateless ref type
  were ever added. `TargetRef` is a closed two-member union today, so this is
  a taste call, not a defect.
- Script launches do not scrub inherited `COGA_SKILL_*` the way agent
  launches do. Pre-existing, and `coga/architecture` only promises the
  discard for agent launches — out of scope here.
- Writer-side "refuse a path outside `coga/tasks/`" defence in depth is
  already owned by `scrub-coga-task-in-the-pytest-autouse-guard-so-fix`,
  which also covers the polluted-ticket cleanup. Correctly left there.

Post-review verification: rebased onto `origin/main` (`9e500327`) — clean,
no conflicts — full suite `1577 passed, 1 skipped`.

## Open-PR conflict discovered 2026-07-29

This task was relaunched from the stale primary branch
`slack-post-nonfatal-after-transition`, whose Coga-state sync had repeatedly
refused to move the authoritative ticket backward. That stale copy produced a
second, peer-reviewed implementation on `bootstrap-no-blackboard` at
`a1fb7b9e`, based on current `main` (`a0632645`).

The authoritative `main` ticket is already at review with PR #671
(`fix/stateless-bootstrap-blackboard`). GitHub reports that PR as
`CONFLICTING`: it still changes `src/coga/commands/launch_script.py`, which the
subsequent script-seam deletion removed. The replacement branch accounts for
that deletion and moves the shared env reset into `apply_task_env`, but
publishing it requires an explicit choice:

1. force-update PR #671's existing head with the replacement commit; or
2. close #671 and publish `bootstrap-no-blackboard` as a new PR.

No second PR was opened and no existing PR ref was rewritten. The stale
checkout's four generated-file edits were preserved recoverably in
`stash@{0}` on `slack-post-nonfatal-after-transition` before returning the
primary checkout to `main`.

## PR

Fixes a Dream worker recipe writing its `## Dream Skill: <name>` run report
into a *packaged* bootstrap `ticket.md` — a shipped wheel resource — when the
recipe is invoked from inside a stateless `bootstrap/*` session.

`build_task_env` set `COGA_TASK_BLACKBOARD` to the launched target's resolved
`ticket_path` for every target. For a bootstrap target that path *is* the
package resource (or a repo-local `coga/bootstrap/<name>/` override), so the
three recipes that append to whatever the variable names corrupted it. PR #596
closed the same class for nested launches by re-deriving `COGA_TASK_*` at the
spawn boundary; this extends that boundary rather than adding writer-side
guards.

Changes:

- `build_task_env` omits `COGA_TASK_BLACKBOARD` for a `BootstrapRef`. Stateless
  bootstrap tickets are command definitions, not mutable task state, so they
  have no blackboard — the writers' existing "no blackboard → stdout" path then
  does the right thing for all three at once.
- Both spawn boundaries (`spawn_agent_session`, `run_script_mode`) drop an
  inherited `COGA_TASK_BLACKBOARD` before overlaying freshly built metadata, so
  a nested stateless launch cannot retain an outer task's blackboard.
- Updated the `coga/architecture` contract (live + packaged) and the packaged
  `coga/cli` context to state the task-backed/stateless split.

Test plan: `python -m pytest` — 1577 passed, 1 skipped. Two new regression
tests, both confirmed failing on pre-fix code: one runs the registered
`validate-drift` recipe from a captured bootstrap agent environment and asserts
the report lands on stdout while a package-shaped `bootstrap/orient/ticket.md`
stays byte-identical; one asserts a stateless bootstrap script sees
`COGA_TASK_BLACKBOARD` unset even when the launching environment sets it.

---

## Blockers

- [x] [2026-07-29 11:39] [agent:nicktoper] id=20260729T113952 PR #671 is now conflicting after the script-seam deletion, while the current-main replacement is peer-reviewed at bootstrap-no-blackboard a1fb7b9e. Decide whether to force-update #671's head with that replacement or close #671 and publish a new PR.
  resolved: [2026-07-29 16:16] [human:nicktoper] Resolved by taking option 1: PR #671's head was force-updated with the current-main replacement and merged as a13fba61 on 2026-07-29 19:20 UTC. Verified the merged diff carries the replacement content (no launch_script.py; writer-side guards in dream_validate_drift.py, dream_cleanup_orphan_markers.py, skill_update.py) and that git diff origin/main bootstrap-no-blackboard -- src/ tests/ is empty, so nothing from the replacement branch is unmerged.
