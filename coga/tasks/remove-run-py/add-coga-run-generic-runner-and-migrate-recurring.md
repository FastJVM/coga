---
slug: remove-run-py/add-coga-run-generic-runner-and-migrate-recurring
title: Add coga run generic runner and migrate recurring jobs
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
step: 2 (review-design)
---

## Description

**Ticket A of 3** in `remove-run-py/`. Add the replacement execution surface
before tickets B and C port the hard consumers and delete the old script seam:
a fixed, legible `coga run <recipe> [args...]` command, plus direct recurring
recipe execution that no longer depends on a skill's `script: run.py`.

The generic command uses ordinary argv as its argument channel. It resolves a
recipe name through one explicit in-package name→function table and passes the
trailing tokens, with their boundaries and option spelling intact, as a Python
list. It does not translate them through `COGA_ARG_1..N` or `COGA_ARGC`.
`COGA_TASK_*` remains a separate task-context contract: an agent invoking a
recipe inherits its current task metadata, while the recurring runner
explicitly supplies the instantiated period task's metadata and scoped
secrets.

Migrate the eight deterministic jobs named below to this runner. Five are thin
entrypoints over existing core functions. Contrary to the seed ticket, the
`skill-update`, `validate-drift`, and `cleanup-orphan-markers` `run.py` files
contain substantial recipe/reporting logic; promote that logic
behavior-neutrally into importable `src/coga/` modules before registering it.
Delete the eight migrated `run.py` entrypoints and their `script:` declarations
in this ticket so the A→B→C sequence really leaves only the two hard and two
vestigial seam consumers. Keep `launch_script.py`, ticket-level `script:`,
script dispatch, and the open-pr/delete-task paths working for the later
tickets.

## Context

Current inventory:

- Thin wrappers: local + packaged `coga/{autoclose/sweep,digest/flush,
  blockers/remind,branch-sweep/sweep}` and packaged
  `bootstrap/recurring-scan`.
- Logic-bearing packaged entrypoints:
  `bootstrap/skill-update/run.py` (273 lines),
  `bootstrap/dream/tasks/validate-drift/run.py` (622 lines), and
  `bootstrap/dream/tasks/cleanup-orphan-markers/run.py` (343 lines).
- The four `coga/*` skills have local copies under `coga/skills/` and packaged
  twins. The three `bootstrap/*` skills are package-backed only. Live recurring
  templates are under `coga/recurring/`; their shipped twins are under
  `src/coga/resources/templates/coga/recurring/`. Files under
  `coga/tasks/recurring/` are instantiated period tasks, not templates.

There is one coordination conflict for the owner to resolve before
implementation: `agree-the-core-vs-skills-move-list-then-execute` is already at
its implement step with an approved plan to move autoclose, blocker-reminder,
and branch-sweep logic from core into skill-local `recipe.py` files. This
ticket's fixed importable dispatch design requires those registered command
implementations to remain in `src/coga/`. See `## Open Questions` on the
blackboard.

## Acceptance Criteria

- [ ] `coga run <recipe> [args...]` is a registered built-in command with
  discoverable help. Unknown recipe names fail with exit 2 and list the known
  names.
- [ ] The runner forwards trailing argv as `list[str]` without an environment
  translation; arguments containing spaces stay one element and recipe options
  such as `--no-fix` reach the recipe parser unchanged.
- [ ] A recipe's integer return code becomes the command exit code. Recipe
  stdout/stderr pass through unchanged, and unexpected exceptions remain loud.
- [ ] The fixed registry contains exactly these ticket-A names:
  `autoclose`, `digest`, `blocker-reminders`, `branch-sweep`,
  `validate-drift`, `cleanup-orphan-markers`, `recurring-scan`, and
  `skill-update`.
- [ ] Recurring templates may declare one optional, non-empty `recipe:` name.
  Template loading and `coga validate` reject an unknown name or an ambiguous
  recipe-plus-script configuration.
- [ ] The five deterministic recurring templates declare the mapped recipe and
  execute it without a TTY or agent:
  `autoclose-merged`, `digest`, `blocker-reminders`, `branch-sweep`, and
  `skill-update`.
- [ ] Recipe-backed period tasks preserve the current lifecycle contract:
  `active → in_progress` before execution; success records the recipe result
  and finishes the one-step task; non-zero exit leaves it unfinished, reports
  the failure, and never silently marks it done. Forced and resumed runs keep
  their existing schedule/status semantics.
- [ ] A recurring recipe receives the period ticket's declared secrets and
  `COGA_TASK_*` metadata, so skill-update still appends `## Skill Update` to the
  period task blackboard. Agent-backed recurring templates still use the
  normal launch path and honor `--agent`.
- [ ] Dream phases 1 and 5 invoke `coga run validate-drift` and
  `coga run cleanup-orphan-markers` directly from the Dream task. Their reports
  land on that task's blackboard through its inherited `COGA_TASK_*` context;
  Dream no longer creates child script tasks for those phases.
- [ ] The three logic-bearing packaged scripts are promoted into importable
  core modules without changing their report text, classifications, safety
  gates, stdout/stderr, or return-code behavior.
- [ ] All eight in-scope `run.py` entrypoints and corresponding `script: run.py`
  lines are gone from local/package resources. Afterward, the only remaining
  declarers are `bootstrap/open-pr`, `bootstrap/delete-task`, and the local +
  packaged `coga/show` and `coga/ticket/finalize` twins.
- [ ] The old seam still works end-to-end for `bootstrap/open-pr`; this ticket
  does not delete or disable `launch_script.py`, ticket `script:`, inline
  scripts, or generic project-local script steps.
- [ ] Live and packaged recurring templates, workflows, and skills changed by
  the migration remain in sync, ignoring only runtime high-water state.
- [ ] The architecture/CLI/reference documentation describes `coga run`, the
  fixed registry, the argv contract, and recipe-backed recurring execution
  while explicitly retaining the old seam as a temporary parallel path.
- [ ] Focused runner/recurring/recipe tests, `python -m pytest`, and
  `coga validate --json` pass.

## Proposed Shape

### 1. Add the fixed runner

- Add `src/coga/runner.py`. Define a small `RecipeFn` protocol equivalent to
  `Callable[[Config, list[str]], int]`, one explicit `RECIPES` mapping, and
  `run_recipe(cfg, name, argv)`. Do not discover files, load entry points, or
  treat installed skills as plugins.
- Add the thin Typer head `src/coga/commands/run.py` and register it in
  `src/coga/cli.py`. Configure the command to accept/forward unknown option
  tokens after the recipe positional rather than parsing recipe-specific
  flags itself. Add `run` to `aliases.BUILTIN_COMMANDS` and to the mutating
  end-of-command Coga-state sweep.
- Keep argument and task context distinct. `argv` replaces only
  `COGA_ARG_*`/`COGA_ARGC`. Move `build_task_env` and the host-repo-root helper
  out of `commands/launch_script.py` into a neutral shared module such as
  `src/coga/task_env.py`; agent launch and the still-live script seam import
  it from there unchanged.

### 2. Expose importable recipe functions

Keep wrappers thin and error behavior explicit. The intended registry targets
are:

| Recipe | Importable target | Migration |
| --- | --- | --- |
| `autoclose` | `coga.autoclose.run_autoclose_recipe` | Adapter around `sweep_merged`; preserve `GhError`/validation handling and quiet-day output. |
| `digest` | `coga.commands.digest.run_digest_recipe` | Adapter around the existing `run_digest`. |
| `blocker-reminders` | `coga.blocker_reminders.run_blocker_reminders_recipe` | Adapter around `remind_blocked_tasks`, preserving count output. |
| `branch-sweep` | `coga.branchsweep.run_branch_sweep_recipe` | Adapter around `sweep_branches`, including git-root and gh/remote failure gates. |
| `recurring-scan` | `coga.recurring_runner.run_recurring_scan_recipe` | Parse ordinary argv for force/interactive/agent/fresh-control inputs and call `run_recurring_scan`; remove the `COGA_RECURRING_*` bootstrap wrapper channel. |
| `skill-update` | `coga.skill_update.run_skill_update_recipe` | Move the current packaged script's update/report code into this module. |
| `validate-drift` | `coga.dream_validate_drift.run_validate_drift_recipe` | Move the current packaged script intact enough that its existing unit tests can import the new module. |
| `cleanup-orphan-markers` | `coga.dream_cleanup_orphan_markers.run_cleanup_orphan_markers_recipe` | Move the current packaged script's candidate/PR-gate/report logic into this module. |

The exact helper names inside those modules may follow existing conventions,
but the public registry names and `RecipeFn` signature are fixed. All no-arg
recipes reject unexpected argv instead of ignoring it.

### 3. Route recurring templates by `recipe:`

- Extend `coga.recurring.Template` with a `recipe` property and validate the
  optional field as a known non-empty registry name. Carry the resolved recipe
  on `DueTask` so the scan and named-launch paths do not infer execution from a
  workflow/skill name.
- In `recurring_runner.py`, choose the recipe path before the existing
  `launch_cmd` path. Run the current interpreter's
  `-m coga.cli run <recipe> ...` with the host repo as cwd and an environment
  built from the period ticket's scoped secrets plus fresh task metadata. This
  keeps process isolation, stdout streaming, and exit codes while replacing N
  script files with one command surface.
- Put the recipe task's start/success/failure bookkeeping beside the recurring
  launch loop. Re-read the ticket after execution before marking it done so a
  report appended to the single-file blackboard is not overwritten. Leave the
  old `is_script_launch` fallback in place for out-of-scope/custom script
  templates until ticket C.
- Add the following fields to both live and packaged templates, and update
  their comments/body plus one-step workflow/skill wording from “script step”
  to “recipe-backed recurring task”:

| Template | `recipe:` |
| --- | --- |
| `autoclose-merged` | `autoclose` |
| `digest` | `digest` |
| `blocker-reminders` | `blocker-reminders` |
| `branch-sweep` | `branch-sweep` |
| `skill-update` | `skill-update` |

Instantiated `coga/tasks/recurring/*` tickets need no hand edit: execution is
selected from their source template, and forced/resumed runs therefore migrate
in place.

### 4. Migrate Dream and remove the entrypoints

- Update the live + packaged Dream template and the two Known Skill Contracts
  so the parent task reads each contract and invokes `coga run validate-drift`
  / `coga run cleanup-orphan-markers` itself. Because an agent launch already
  receives `COGA_TASK_*`, the promoted recipes append their existing sections
  directly to the Dream task blackboard. Remove the now-unused child-script
  workflow resources.
- Delete the four local and four packaged `coga/*/run.py` twins, the three
  package-only logic-bearing `run.py` files, and packaged
  `bootstrap/recurring-scan/{ticket.md,run.py}`. Remove `script: run.py` from
  their SKILL.md files and rewrite the runnable instruction as the registered
  `coga run` spelling.
- Update packaging/init assertions and the CLI, architecture, codebase, and
  public command reference. Do not remove the old seam documentation yet;
  describe the transitional coexistence, leaving final seam deletion wording
  to ticket C.

### 5. Verification

- Add focused command tests for registry lookup, raw argv boundaries/options,
  return-code propagation, and stdout/stderr.
- Repoint the existing skill-update and Dream unit tests from dynamic
  `run.py` loading to the promoted modules. Replace script-launch integration
  tests with recurring-recipe and inherited-task-context tests.
- Extend recurring tests for template validation, no-TTY recipe dispatch,
  lifecycle success/failure, forced/resumed behavior, scoped secrets, and the
  unchanged agent fallback. Keep an explicit open-pr stateless-script smoke
  test as the receipt that ticket A did not delete the old seam.

## Out of Scope

- Porting `bootstrap/open-pr` or `bootstrap/delete-task`; ticket B owns their
  ownership gates, bare-URL/stdout contract, and launch-script coupling.
- Deleting `commands/launch_script.py`, ticket/skill `script:` support,
  `is_script_launch`, inline scripts, or generic project-local script
  workflows; ticket C owns the seam deletion after A and B merge.
- Removing the vestigial `coga/show` and `coga/ticket/finalize` wrappers or
  their environment-only entrypoints; ticket C owns them.
- Dynamic/user-defined recipe discovery, a plugin API, config-driven imports,
  aliases for every recipe, or a new recipe field on ordinary task
  frontmatter. The registry is intentionally a fixed Coga command surface.
- Changing schedules, recipe policy, Dream classifications, report formats,
  cleanup safety gates, or notification semantics.
- Editing historical/done task prose merely because it mentions `run.py`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design investigation (2026-07-23)

- The current-code inventory does not match the ticket's "each `run.py` is a
  ~20-line wrapper over `coga.*`" premise. The four local recurring wrappers
  and packaged `bootstrap/recurring-scan/run.py` are thin, but packaged
  `bootstrap/skill-update/run.py` (~250 lines),
  `bootstrap/dream/tasks/validate-drift/run.py` (~620 lines), and
  `bootstrap/dream/tasks/cleanup-orphan-markers/run.py` (~340 lines) own
  substantial recipe/reporting logic that has no importable `src/coga/`
  equivalent. Removing those files requires a behavior-neutral promotion, not
  only a dispatch-table entry.
- `agree-the-core-vs-skills-move-list-then-execute` is already at its implement
  step with an owner-approved plan to move autoclose, blocker-reminder, and
  branch-sweep recipe logic in the opposite direction: from `src/coga/` into
  skill-local `recipe.py` files. Its implementation and this ticket's stated
  "dispatch over existing `coga.*` core modules" cannot both land unchanged.
- Only the four `coga/*` skills have live copies under `coga/skills/`.
  `bootstrap/skill-update` and the two Dream worker skills are package-backed
  only. Recurring templates live under `coga/recurring/` (with packaged twins
  under `src/coga/resources/templates/coga/recurring/`);
  `coga/tasks/recurring/` contains instantiated period tasks, not templates.
- The existing recurring path gets its deterministic/agent distinction from
  `script:` on the template or first workflow skill. A replacement therefore
  needs an explicit recipe declaration on recurring templates, task-context
  environment for recipes that append to a blackboard, and lifecycle handling
  equivalent to script success/failure. A dispatch table alone is insufficient.

## Open Questions

1. **Which direction wins for the three recipes also owned by
   `agree-the-core-vs-skills-move-list-then-execute`?** Recommended ruling:
   registered `coga run` recipes are real command implementations and therefore
   remain importable under `src/coga/`; cancel or revise those three approved
   moves before this ticket's implement step. The alternative is a
   path/importlib loader for skill-local `recipe.py` files, which contradicts
   this ticket's core-function premise and adds a plugin-like indirection.
2. **Is the corrected scope still one PR?** Recommended ruling: yes. The three
   unexpectedly large entrypoints already have focused tests, and their
   promotion should be mostly file moves plus import updates; keeping them here
   leaves the A→B→C dependency honest. If the owner does not want roughly 1,200
   lines of recipe promotion in A, split those three into an A2 dependency and
   make both B and C wait for it rather than pretending the functions already
   exist in core.
