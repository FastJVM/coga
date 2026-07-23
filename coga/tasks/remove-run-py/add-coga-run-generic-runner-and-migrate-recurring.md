---
slug: remove-run-py/add-coga-run-generic-runner-and-migrate-recurring
title: Add coga run generic runner and migrate recurring jobs
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
step: 1 (design)
---

## Description

**Ticket A of 3** in `remove-run-py/` (removing Coga's script-seam). This one
builds the replacement and migrates the easy consumers; it is deliberately
non-destructive — the old seam stays alive alongside the new runner. Deleting
the seam is ticket C.

Add a single generic runner — `coga run <recipe> [args...]` — backed by a
name→function dispatch table over the recipe functions that already live in
`coga.*` core modules. Then migrate every deterministic recurring job off its
`script: run.py` skill so the recurring runner invokes `coga run <recipe>`
directly instead of launching a script step.

The `design` step produces the reviewable spec: the runner's arg channel (what
replaces `COGA_ARG_*` / `COGA_ARGC`), how a recipe name resolves to a function,
where the dispatch table lives, and the exact per-job migration. Owner reviews
that spec before implementation.

Done: `coga run <recipe>` exists and is tested; the recurring jobs below run via
it (their `run.py` files can be deleted here since they are pure wrappers, or
left for ticket C — the design spec decides, but no *other* consumer changes);
the old `script:` seam still functions for open-pr; suite + `coga validate` pass.

## Context

**In scope — the genuinely-thin recurring jobs only:** `coga/autoclose/sweep`,
`coga/digest/flush`, `coga/blockers/remind`, `coga/branch-sweep/sweep`,
`bootstrap/dream/tasks/validate-drift`, `bootstrap/dream/tasks/cleanup-orphan-markers`,
`bootstrap/recurring-scan`, `bootstrap/skill-update`. Each `run.py` is a ~20-line
entrypoint over an existing `coga.*` function (e.g.
`coga/skills/coga/blockers/remind/run.py` → `coga.blocker_reminders.remind_blocked_tasks`),
so the recipe logic already exists and does not move.

**Explicitly NOT in this ticket:** the two seam-integrated *hard* consumers —
`open-pr` and `delete-task` — whose recipes are not in `coga.*` modules and
which carry real ownership/stdout/subprocess logic (both are ticket B); and
deleting `launch_script.py`, the `script:` frontmatter field, `is_script_launch`
dispatch, or the docs (ticket C). Keep the old seam runnable.

**Dependency order:** A (this) → B (`port-hard-consumers`) → C
(`delete-the-script-seam`). B needs this runner; C must run only after A and B
leave zero *live* seam consumers.

**Sync:** every `run.py` and skill has a live copy under `coga/skills/` and a
packaged twin under `src/coga/resources/templates/coga/bootstrap/skills/...`;
keep them in sync. Recurring templates live under `coga/tasks/recurring/`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
