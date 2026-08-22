---
slug: migrate-recurring-templates-to-ticket-py-shims-and
title: 'Migrate recurring templates to ticket.py shims and delete recipe:'
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/codebase
- coga/recurring
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

PR 2 of the script-ticket work: once the classifier from
`recurring-recipe-question` (PR 1) has landed, migrate the five recipe-backed
recurring templates onto `ticket.py` shims, delete the `recipe:` field
entirely, and run the full prose-contract sweep. The authoritative spec is the
parent ticket's **Proposed Shape** — especially *"The recurring shims (PR 2),
concretely"* and *"The split"* — accepted by the owner at `review-design` on
2026-08-18. Do not redesign; execute that spec.

Concretely:

- One eight-line shim per template (no shared dispatcher): `ticket.py` beside
  each of the five recipe-backed templates, importing the core recipe function
  and completing the step via the CLI (`coga bump` subprocess, never an
  in-process Typer call — `OptionInfo` sentinel gotcha).
- `_create_at_slug` copies `ticket.py` from the template directory into the
  created period task directory (only `ticket.py`; other siblings like
  `digest/spool.md` stay with the template).
- Delete `recipe:`: `Template.load`, `Template.recipe`, `DueTask.recipe`,
  `_run_recipe_task`, and both TTY pre-filters (replaced by
  `script_entry_point(...) is not None`).
- Reshape the five one-step workflows and their skills; sync the `digest/post`
  live↔packaged workflow copies (live copy currently missing).
- Prose sweep: `coga/recurring`, `coga/cli`, `coga/sync`, `coga/patterns`,
  `coga/roadmap`, `marketing/positioning`, `README.md`, `docs/vision.md`,
  `docs/concepts.md`, `docs/reference.md`, `docs/market-thesis.md`,
  `docs/cli-extension-audit.md` — plus packaged twins.

## Context

- **Blocked on PR 1.** Do not start until `recurring-recipe-question`'s PR has
  merged; the shims depend on `launch_script.py`, `script_entry_point`, and
  `COGA_TASK_STEP` existing. The intermediate state is coherent: a template
  with `recipe:` and no `ticket.py` keeps taking the old path until this ticket
  lands.
- **Owner decisions already made** (recorded on the parent blackboard,
  2026-08-18): entry point is `ticket.py` exactly; v1 scripts take no operands
  (`sys.argv[1:] == []` — no `COGA_ARG_*` revival); the completion-contract
  classifier (script closes its own step or the agent follows) is the accepted
  rule; `runner.RECIPES` and `coga run` survive unchanged as a public command
  surface.
- **Packaging trap:** packaged template dirs gaining a `.py` file flip from
  "pure data" to "contains Python" — the documented package-walk vs
  `force-include` wheel collision (`coga/codebase`, "Wheel packaging"). Verify
  the wheel builds on a **pristine** clone, not just a dev tree.
- **Tests:** shims are covered from `tests/` by subprocessing the entry point
  against the seeded `example/` fixture — never by collecting the live
  dogfooded `coga/` tree.
- Migrating the ten `runner.RECIPES` implementations out of `src/coga/`, and
  any behavior change to the recipes themselves, stay out of scope — same as
  the parent ticket.

<!-- coga:blackboard -->

## Dev

branch: recurring-ticket-py
worktree: /tmp/coga-recurring-ticket-py

## Plan (2026-08-21, implement)

PR 1 (#700, `2343a9f6`) is merged on `main`, so this ticket is unblocked.
Executing the parent's Proposed Shape verbatim; no redesign.

1. **Five shims.** `ticket.py` beside each recipe-backed template
   (`autoclose-merged`, `blocker-reminders`, `branch-sweep`, `digest`,
   `skill-update`), live under `coga/recurring/` and packaged under
   `src/coga/resources/templates/coga/recurring/`. Each imports its core
   recipe function + `load_config`, runs it, and on zero completes the step
   with a `coga bump` **subprocess** (never in-process Typer — `OptionInfo`
   sentinels).
2. **`_create_at_slug` copies `ticket.py`** from the template dir into the
   created period task dir. Only that name; `digest/spool.md` stays put.
3. **Delete `recipe:`** — `Template.load` validation, `Template.recipe`,
   `DueTask.recipe`, `_run_recipe_task`, `_launch_created`'s recipe branch,
   both TTY pre-filters (→ template-level `ticket.py` presence), and
   `validate.py`'s recipe check.
4. **Workflows/skills** — reshape the five one-step workflows and their
   skills from "recipe-backed / `coga run X`" to "deterministic `ticket.py`";
   add the missing live `coga/workflows/digest/post.md` + packaged twin.
5. **Prose sweep** — `coga/recurring`, `coga/cli`, `coga/sync`,
   `coga/patterns`, `coga/roadmap`, `marketing/positioning`, `README.md`,
   `docs/{vision,concepts,reference,market-thesis,cli-extension-audit}.md`,
   plus packaged twins.
6. **Tests** — subprocess the shims against the seeded `example/` fixture;
   never collect the live dogfooded `coga/` tree.

### Decisions taken here (recorded, not redesigned)

- **Keep `assignee: agent` on the five one-step workflow steps.** The design's
  legibility note calls it "false", but `VALID_ASSIGNEE_ROLES` has no script
  token, adding one would be the mode field the parent forbids, and PR 1's own
  seeded fixture (`example/coga/workflows/deterministic/check.md`) ships
  `assignee: agent` on a script-only step. Changing it is churn with lifecycle
  risk and no stated requirement.
- **The sweep's `launch` call must not let a script failure `SystemExit` past
  `run_recurring_scan`.** `_run_recipe_task` returned the code so the command
  could still run its exit-boundary git sync; `launch`'s `_exit_failed_script`
  raises `SystemExit`. Catch it at the call site and return the code, matching
  the old `if code: return code`.
- **The TTY pre-filter becomes a template-level check.** `script_entry_point`
  takes a `TargetRef`; at pre-filter time the period task does not exist yet,
  so the equivalent question is asked of the template directory
  (`<template>/ticket.py`), which is exactly what `_create_at_slug` will copy.

## Implement results (2026-08-21)

Commit `b3946b07` on `recurring-ticket-py` (worktree
`/tmp/coga-recurring-ticket-py`). Every checklist item in the description is
done; nothing was left out.

### What landed

- **Five shims**, live under `coga/recurring/<name>/ticket.py` and packaged
  under `src/coga/resources/templates/coga/recurring/<name>/ticket.py`, kept
  byte-identical and registered in `IDENTICAL_LIVE_PACKAGED_PAIRS`. Each
  imports `load_config` plus its one core recipe function, runs it, and on zero
  completes the step with a `coga bump` **subprocess**.
- **`_create_at_slug` copies `ticket.py`** into the created period task and
  nothing else; it raises rather than silently dropping the deterministic half
  if the created task were ever file-form.
- **`recipe:` deleted** — `Template.load` validation, `Template.recipe` (now
  `Template.script_entry_point`), `DueTask.recipe`, `_run_recipe_task` (117
  lines), `_launch_created`'s recipe branch, and both TTY pre-filters.
  `runner.RECIPES` and `coga run` are untouched.
- **`coga recurring` has no dispatch left.** Every template — bare sweep,
  `--force`, and `recurring launch <name>` — goes through one `coga launch`
  call, so both paths deduce identically by construction.
- **Workflows/skills reshaped**; live `coga/workflows/digest/post.md` added
  (identical to its packaged `bootstrap/workflows/` twin, now registered as a
  pair).
- **Prose sweep** over every file the description lists, plus three the sweep
  list omitted but the change made actively false: `coga/architecture`
  (`recipe:` dispatch, the env contract's "recurring recipe subprocess"),
  `coga/codebase` (the layout tree), `coga/important` / `coga/current-direction`
  (wording). `docs/concepts.md` and `docs/vision.md` also still claimed launch
  *always* spawns an agent — false since PR 1, fixed here.

### Decisions and deviations, with reasons

- **`recipe:` is now inert, not an error.** The design frames the deletion as a
  format change and puts scrubbing legacy `script: null` keys out of scope, so
  a leftover key is ignored the same way. This is safe in practice: all five
  live templates and all five packaged templates are migrated in this commit,
  and a stale hand-edited template would deduce agent, then be skipped loudly
  by the TTY gate with a Slack scan-error summary — not silently.
- **Validate keeps a template-level check.** Deleting the `recipe:` registry
  check would have left a template's `ticket.py` unvalidated until its next
  firing, and it is copied into every period task. `_check_script_entry_point`
  was split so recurring templates get the same compile check tasks already
  got in PR 1. This is the direct replacement of the deleted check, not new
  scope.
- **`launch`'s `SystemExit` is converted back to a return code** in both sweep
  entry points. `_run_recipe_task` returned its code so the command still ran
  its exit-boundary git sync; `_exit_failed_script` raises. Without this the
  process would unwind past that sync. A zero-code `SystemExit` continues the
  sweep rather than truncating it.
- **`assignee: agent` kept on the five one-step workflow steps.** The design
  calls it "false", but `VALID_ASSIGNEE_ROLES` has no script token and adding
  one would be the mode field the parent forbids; PR 1's own seeded fixture
  (`example/coga/workflows/deterministic/check.md`) ships `assignee: agent` on
  a script-only step. Changing it is churn with lifecycle risk and no stated
  requirement.

### Verification

- `1890 passed` (full suite, `hatchling` present so **all five** packaging
  tests ran — including the wheel build that normally skips).
- **Pristine-clone wheel build**, the trap the ticket flags: `git clone` of the
  branch into `/tmp/coga-pristine` (no `coga init` symlink views), then
  `pip wheel --no-build-isolation`. Builds clean, and all five `ticket.py`
  files ship in the wheel. The packaged recurring dirs flipping from pure-data
  to containing Python does not collide: they are grabbed by the `packages`
  walk and are not force-included.
- `coga validate --json`: seeded example clean (`ok_count: 3`, zero issues);
  this repo reports `ok_count 117, issues 26`, byte-identical to `main`'s
  baseline — all pre-existing and unrelated.
- **Migration is clean on disk**: all five live `coga/tasks/recurring/*/`
  period tasks are `status: done`, so the next sweep deletes and recreates them
  from the migrated templates. No live period task is stranded without its
  `ticket.py`.
- Freshness: fetched and rebased onto `origin/main` — zero behind, one ahead,
  clean tree. No push, no PR (that is the `open-pr` step).

### New test coverage

- `tests/test_recurring_shims.py` — per-shim contract (the imported symbol
  **is** `RECIPES[name]`, argv read structurally from the AST so reformatting
  cannot retire the check, no in-process bump import), plus two end-to-end runs
  against a copy of the seeded `example/` fixture using the real packaged
  `blocker-reminders` shim: success closes its own step to `done`; a non-zero
  exit leaves the task `in_progress` with no agent work.
- `tests/test_recurring.py` — the copied `ticket.py` runs with the period
  task's scoped secrets and `COGA_TASK_*`; the sweep returns a failed script's
  exit code instead of unwinding.
- `tests/test_validate.py` — a broken template `ticket.py` is reported before
  any period task exists; a leftover `recipe:` key is not an error.

## Peer review (2026-08-21)

- Ran `codex review --base main`. It found three material regressions: recurring
  script failures had fallen back to the routine notification channel, a
  script-owned `coga block` was overwritten with `paused`, and the packaged
  `coga/patterns` context still taught the deleted `recipe:` format.
- Commit `7a5d4d69` fixes all three. Recurring opts the shared launcher into
  important failure routing; the launcher reports a script-only stop so the
  sweep preserves a deterministic blocker without changing the intentional
  pause contract for agent-owned blockers; and the packaged patterns copy is
  synced and guarded as a live/package pair.
- The final contract sweep also corrected active stale launch text in the
  packaged `coga/cli` context, both `coga/principles` copies, the v2 parking-area
  guide, and the autoclose module contract.
- Re-fetched and rebased on `origin/main` after review: zero behind, two commits
  ahead, clean worktree. Verification: `1894 passed`; task-scoped validation
  clean apart from the isolated worktree's missing gitignored local-user warning;
  pristine-clone wheel build succeeded with all five shims and corrected
  packaged contexts present.

## PR

Migrate the five deterministic recurring templates from `recipe:` declarations
to exact-sibling `ticket.py` shims, route every recurring run through the shared
launch classifier, and update the live and packaged execution contracts. The
review follow-up preserves important failure alerts and script-owned blockers.

Test plan: `python -m pytest` (1,894 passed); pristine-clone wheel build passed
with all five packaged shims present.
