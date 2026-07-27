---
slug: recurring-bugs/dream-recipes-write-reports-into-packaged-bootstra
title: Dream recipes write reports into packaged bootstrap tickets
status: active
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
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
script: null
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
