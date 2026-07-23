---
slug: remove-run-py-everywhere
title: remove run.py everywhere
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
script: null
---

## Description

Remove Coga's launch-integrated script-seam entirely and replace it with a
single generic runner. Today a skill or ticket declares `script: run.py` (or a
sibling/inline script), and `coga launch` detects that via `is_script_launch`
and runs it with no agent through `launch_script.py`. That seam is spread across
the ticket model and shows up as ~6 live + ~12 packaged `run.py` wrapper files,
each of which is only a thin entrypoint over a recipe that already lives in a
`coga.*` core module.

The goal is to delete the seam — no `script:` frontmatter field, no
`is_script_launch` branching in `launch`, no `launch_script.py`, no
`COGA_ARG_*` env plumbing, no per-skill `run.py` — and replace it with one
generic `coga run <recipe>` command backed by a name→function dispatch table
over the existing recipe modules. Deterministic recurring jobs and the PR path
invoke that runner directly instead of being launched as a script step.

Why: the seam is confusing and duplicative. The real logic already lives in
`coga.*` modules; the `run.py` files, the `script:` field, and the 520-line
`launch_script.py` are wrapper machinery threaded through `launch`, `recurring`,
`megalaunch`, `validate`, `views`, and more. Collapsing it to one runner removes
a whole concept from the ticket model and stops `run.py` from proliferating.

Done looks like: no `run.py` files remain (live or packaged), the `script:`
concept is gone from the ticket model and validation, every deterministic job
that used to be script-launched now runs via the generic runner, and the test
suite plus `coga validate` pass.

## Context

**This is a large, cross-cutting refactor — hence the design-first workflow.**
The `design` step should produce a concrete spec (new runner shape, dispatch
table location, per-consumer migration, deletion order) for the owner to review
before any code is written.

Current seam, for grounding:

- `script: run.py` skills run without an agent. Example:
  `coga/skills/coga/blockers/remind/run.py` is ~20 lines that import
  `coga.blocker_reminders.remind_blocked_tasks` and call it. All the real logic
  is already in the core module; the wrapper is the only thing being removed.
- Live wrappers: `coga/skills/coga/{show,branch-sweep/sweep,autoclose/sweep,
  blockers/remind,digest/flush,ticket/finalize}/run.py`. Packaged copies live
  under `src/coga/resources/templates/coga/bootstrap/...` (open-pr,
  recurring-scan, skill-update, delete-task, dream/{cleanup-orphan-markers,
  validate-drift}, plus the mirror of the live ones). Live and packaged copies
  must stay in sync.
- Dispatch entrypoint: `src/coga/commands/launch_script.py` (~520 lines) exposes
  `is_script_launch`, `current_step_is_script`, `run_script_mode`.
- The `script:` field is consumed across `launch.py`, `create.py`,
  `megalaunch.py`, `recurring.py`, `recurring_runner.py`, `skill.py`,
  `tasks.py`, `ticket.py`, `validate.py`, `views.py`, `delete_task.py`,
  `aliases.py`.
- Tests to update: `tests/test_launch_script.py`, `test_launch.py`,
  `test_launch_auto.py`, `test_commands.py`, `test_recurring.py`,
  `test_autoclose_sweep.py`, `test_open_pr_command.py`.

Three distinct consumers of the seam, each needs a replacement path:

1. **Deterministic recurring jobs** — `autoclose/sweep`, `digest/flush`,
   `blockers/remind`, `branch-sweep`, `dream/{validate-drift,
   cleanup-orphan-markers}`, `recurring-scan`, `skill-update`. The recurring
   runner currently launches these as script steps; it must instead invoke the
   generic runner by recipe name.
2. **Command tickets invoked as a verb** — `coga open-pr <slug>` rewrites to
   `launch bootstrap/open-pr` and runs `open-pr/run.py` as a stateless script,
   emitting a bare PR URL on stdout. The verb + its stdout contract must survive
   on the new runner (e.g. `coga run open-pr <slug>`), including
   `COGA_ARG_*`-style argument passing being replaced by the runner's own arg
   channel.
3. **The `open-pr` workflow step** — `code/open-pr` is a script-backed step in
   `code/with-review` and `code/design-then-implement` (the `requires: pr`
   step). Removing the seam means this step moves to the new runner.

**Self-hosting caveat / deletion order.** This very ticket ships on
`code/design-then-implement`, whose own `open-pr` step is `code/open-pr` — a
script step. The implementer must land the replacement PR-opening path
before/atomically-with removing the old seam, or the final `open-pr` step will
break and the owner opens that PR by hand. Call this out in the design spec.

**Docs to update in the same PR** (behavioral contract per CLAUDE.md): the
`run.py` seam is documented in `coga/architecture/SKILL.md` (the
`ticket.md` + `run.py` seam section, around line 594) and referenced in
`coga/sync/SKILL.md`; update both live and packaged copies.

**Out of scope / not a code change:** the ~40 `run.py` mentions in old/done
`coga/tasks/*.md` prose are historical narrative in finished tickets — leave
them; editing done tickets' text changes no behavior.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
