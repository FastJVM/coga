---
slug: decide-what-belongs-in-core-vs-skills-and-move-ski
title: Decide what belongs in core vs skills and move skill-only recipes out of src
  coga
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
step: 4 (review)
---

## Description

Two-part task: **(1) decide the policy** for what legitimately lives in the core
Python package (`src/coga/`) versus in a skill directory, then **(2) move the
skill-only recipes that the policy says don't belong in core** out into their
skill dirs.

This generalizes the open-pr fix (PR #517, which moved `src/coga/open_pr.py` →
`coga/skills/code/open-pr/recipe.py`) and the CLAUDE.md rule it produced
("extend at the edges, not the core"). The open question that fix left open is
*where the line is* — this ticket settles it and applies it.

### Part 1 — write the policy (do this first; it's the real deliverable)

The policy is **decided** (owner, 2026-07-17): **keep core minimal, like a
microkernel.** Write the rule into **both** `CLAUDE.md` and the `coga/codebase`
context (keep the two phrasings consistent). The rule:

- **Core (`src/coga/`) holds only two kinds of code:** (a) genuine **shared
  infra** — code with ≥2 real consumers (compose, config, tasks, launch
  machinery, the autoclose parsers); and (b) a real **command implementation**
  that genuinely needs Python logic and can't be expressed as an alias. That's
  the whole kernel.
- **Everything else is a bootstrap ticket** — a stateless launch target
  (`bootstrap/<name>/ticket.md`) naming a **skill or ticket-owned script**,
  with its deterministic logic in the skill dir beside `run.py`, importing only
  shared core infra, never living in `src/coga/`. This covers user-facing
  workflow recipes (a `code/*` step a user runs, like open-pr) *and*
  coga-internal recurring maintenance recipes.
- **A command surface for such a target is an alias, not core Python** — an
  argv rewrite in `[aliases]` (`dream = "recurring launch dream"`,
  `chat = launch bootstrap/orient`), never a Typer command with logic. So
  **"backs a CLI command" is not by itself a pass into core**: ask whether the
  command is a real Python implementation or just an alias to a launch target.
  Only the former justifies core.
- **The recurring-maintenance carve-out is rejected.** Strict consistency wins
  over the "it's internal, leave it in core" argument: a single-consumer sweep
  is a skill/bootstrap recipe even though coga itself is the only one running
  it. Being internal is not a license to sit in the kernel; only genuine shared
  infra or a real command implementation is.

This generalizes PR #517 (open-pr) into a stated line, and supersedes the softer
"extend at the edges, not the core" phrasing with the concrete microkernel test
above.

### Part 2 — apply it

Move all three recurring-maintenance recipes out of core into their skill dirs
(sibling module beside `run.py`, imports only shared core infra): `sweep_merged`
/ `GhError`, `blocker_reminders` / `remind_blocked_tasks`, and `branchsweep` /
`sweep_branches`. For `sweep_merged`, split `autoclose.py` — the shared parsers
stay in core, the sweep moves to the skill. Keep live + packaged template copies
in sync, move the tests alongside their recipes, run the full suite.

## Context

Inventory of what backs each script skill (from investigation on 2026-07-06):

**Stays core — genuine shared infra (≥2 consumers):**
- `authoring.py` (`finalize_authored_from_env`) — also backs `coga ticket` /
  `coga project`.
- `autoclose.py` **parsers** (`parse_worktree_path`, `parse_branch_name`,
  `parse_pr_url`) — shared by the open-pr recipe and 2 other call sites.

**Command-backed, but re-examine under the alias test (see Part 1):** the
refined rule says "backs a CLI command" is not by itself a pass into core — the
question is whether the command is a real Python implementation or could be a
bootstrap ticket fronted by an alias.
- `commands/digest.py` (`run_digest`) — backs `coga digest`.
- `megalaunch.py` — backs `coga megalaunch`.

These two were filed as "definitely core" under the earlier phrasing. Assess
them against the refined test; if either is really "launch this target," it
becomes a bootstrap ticket + alias. **Scope note:** flag the finding on the
blackboard, but do not expand this PR into moving them without owner sign-off —
Part 2's committed scope is the three recurring-maintenance recipes.

**Skill-only recipes still in core — the candidates to move (all back
coga-internal recurring maintenance, no command, no other consumer):**
- `autoclose.py` `sweep_merged` / `GhError` — backs `coga/autoclose/sweep`.
- `blocker_reminders.py` (`remind_blocked_tasks`) — backs `coga/blockers/remind`.
- `branchsweep.py` (`sweep_branches`) — backs `coga/branch-sweep/sweep`.

**Already done (the precedent):** `code/open-pr` — recipe moved out of core in
PR #517.

**Follow-up ticket (not this one):**
`rewrite-coga-base-prompt-and-agent-mode-block` — rewrites the base prompt and
agent-mode block to speak the microkernel framing. Sequenced after this ticket.

Note the wrinkle for `sweep_merged`: it lives in `autoclose.py` alongside the
shared parsers, so moving it means splitting that module (parsers stay, sweep
goes to the skill) — decide whether that split is worth it or whether cohesion
argues to leave it.

<!-- coga:blackboard -->

## Dev
branch: microkernel-move-recipes
worktree: ../coga-microkernel-move-recipes
pr: https://github.com/FastJVM/coga/pull/618

## PR

### Summary

- Define the microkernel boundary in both agent guides and the `coga/codebase`
  context: shared infrastructure and genuine command implementations stay in
  core; single-consumer recipes live with their skills.
- Move the autoclose, blocker-reminder, and branch-sweep maintenance recipes
  from `src/coga/` into synchronized live and packaged skill directories while
  retaining the shared autoclose parsers and GitHub helpers in core.
- Repoint tests, packaging coverage, recurring templates, workflow contracts,
  and adjacent documentation at the skill-local recipes.

Test plan: `python -m pytest` (`1361 passed, 1 skipped`).

## Implementation complete (implement step, 2026-07-20)

Committed on `microkernel-move-recipes` (1 commit, rebased onto current
`origin/main`). Not pushed — that is the `open-pr` step.

**Part 1 — policy written** into `CLAUDE.md` (new "Keep core minimal — the
microkernel rule" subsection) and the `coga/codebase` context (new "What
belongs in core vs a skill — the microkernel rule" section). Consistent
phrasing; both state the two-kinds-of-core test, the alias-not-Typer point, and
the consumer test that keeps a shared symbol in core.

**Part 2 — three recipes moved** to `recipe.py` beside `run.py` (live +
packaged copies):
- `coga/autoclose/sweep` — `sweep_merged` + `_try_bump_one` / `_candidate` /
  `_on_final_step` / `_read_pr_url` / `parse_pr_number` moved; `autoclose.py`
  split so `GhError` / `pr_state` / the three parsers stay in core (they have
  other consumers: `branchcleanup`→`retire`, branch-sweep recipe, Dream
  orphan-marker). recipe re-exports `GhError` so run.py pulls the sweep surface
  from one place.
- `coga/blockers/remind` — `blocker_reminders.py` deleted from core, moved
  wholesale.
- `coga/branch-sweep/sweep` — `branchsweep.py` deleted from core, moved
  wholesale (still imports shared `branchcleanup` + `autoclose` from core).

**Mechanism:** run.py does `sys.path.insert(0, dirname(__file__))` then
`from recipe import …` — works both as `python run.py` (launcher) and when a
test loads run.py via `spec_from_file_location`. Tests load recipes via a new
`conftest.load_skill_recipe(ref)` helper; sweep-behavior monkeypatches moved to
the recipe module's `pr_state` binding.

**Coverage added:** recipe.py entries in `test_packaging` (wheel + source), the
autoclose live↔packaged sync pair, and identical-pairs guards for the
blocker/branch-sweep run.py+recipe.py (previously unguarded).

**Assessment recorded (no move):** `commands/digest.py` (`run_digest`) and
`megalaunch.py` are real command implementations with genuine Python logic, not
"launch this target" aliases — they legitimately stay core under the rule. No
owner sign-off needed since nothing moved; documented per the ticket's scope
note.

**Verification:** full suite `1361 passed, 1 skipped` on the rebased tree;
`coga validate` 0 errors; each run.py smoke-imports its sibling recipe.

## Peer review (Codex, 2026-07-20)

`codex review --base origin/main` found three consistency issues; the recipe
moves themselves passed the full suite and an end-to-end package-backed script
launch smoke test.

- The policy used `code/open-pr` as a current skill-recipe example even though
  PR #585 later made it a genuine Python command implementation in core.
- The new repository guidance was added to `CLAUDE.md` but not `AGENTS.md`, so
  the two configured agent CLIs would receive different placement rules.
- The autoclose and branch-sweep workflow contracts still named the removed
  `coga.autoclose.sweep_merged` / `coga.branchsweep.sweep_branches` APIs.

Resolved all three findings in rebased commit `9c1ddb00`, including matching
live and packaged workflow copies plus adjacent dead-path documentation. The
branch was fetched and rebased unconditionally onto fresh `origin/main`
(`b6e004be`), then the full suite passed again: `1361 passed, 1 skipped`.
`AGENTS.md` and `CLAUDE.md` are byte-identical, `git diff --check` is clean,
and the feature worktree is clean with two commits ahead of `origin/main`.
`coga validate --task decide-what-belongs-in-core-vs-skills-and-move-ski
--json` reports 1 valid task and no issues.

## Plan (implement step, 2026-07-20)

Two parts. **Part 1 (policy)** = write the microkernel rule into `CLAUDE.md`
and `coga/codebase` SKILL.md (both live + packaged copy). **Part 2 (apply)** =
move the three recurring-maintenance recipes out of `src/coga/` into their skill
dirs as a `recipe.py` sibling beside `run.py`.

### Key refinement to the 2026-07-06 inventory (applying the policy strictly)

The inventory said "move `sweep_merged` / `GhError`". Investigation shows
`GhError` **and** `pr_state` have real consumers *outside* the sweep:
`src/coga/branchcleanup.py` (core; used by `coga retire` + the branch-sweep
recipe) imports both, and `dream/cleanup-orphan-markers` uses `pr_state`. By the
microkernel test itself (≥2 real consumers = shared infra stays), they **must
stay in core** — moving them would force core (`branchcleanup.py`) to import
from a skill dir, the exact anti-pattern the policy forbids. This *is* the
policy resolving the "wrinkle" the ticket flagged, not a scope cut.

So the autoclose split is:
- **Stays in core `autoclose.py`:** `GhError`, `pr_state`, and the parsers
  `parse_pr_url` / `parse_branch_name` / `parse_worktree_path` (all shared).
- **Moves to `coga/skills/coga/autoclose/sweep/recipe.py`:** `sweep_merged`,
  `_try_bump_one`, `_candidate`, `_on_final_step`, `_read_pr_url`,
  `parse_pr_number` (+ its `_PR_NUMBER_RE`) — all sweep-only.
  Recipe imports `GhError`/`pr_state`/`parse_pr_url` from `coga.autoclose`
  (shared core), plus `mark_done`, `Config`, taskfile/tasks/ticket helpers.

`blocker_reminders.py` and `branchsweep.py` are fully skill-only (only their
run.py + test consume them) → move wholesale to their `recipe.py`, delete the
core module. `branchsweep` recipe still imports `branchcleanup` +
`autoclose` (both shared core) — correct.

### run.py → recipe import mechanism

Scripts run as `python <skill>/run.py`, so `sys.path[0]` is the skill dir and a
bare `import recipe` resolves. But the sync/skill tests load `run.py` via
`spec_from_file_location`, where sys.path[0] is NOT the skill dir. So each
run.py adds its own dir to sys.path before importing the sibling:
`sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`. Boring,
obvious, works both ways.

### Two copies each (dogfood + package) — keep in sync
- Live:     `coga/skills/coga/<...>/{SKILL.md,run.py,recipe.py}`
- Packaged: `src/coga/resources/templates/coga/bootstrap/skills/coga/<...>/...`
Add `recipe.py` to: the live↔packaged sync test, `tests/test_packaging.py`
`_EXPECTED` list.

### Tests
- `test_autoclose.py`: parser tests stay on `coga.autoclose`; sweep_merged /
  parse_pr_number tests move to load the recipe module.
- `test_blocker_reminders.py` / `test_branchsweep.py`: repoint imports from the
  core module to the recipe module (loaded via importlib helper).

### FLAGGED for owner (Part 1 scope note, do NOT move here)
`commands/digest.py` (`run_digest`, backs `coga digest`) and `megalaunch.py`
(backs `coga megalaunch`) are the "re-examine under the alias test" pair. Both
are real Python command implementations with genuine logic (not "launch this
target"), so under the microkernel test they legitimately stay core as command
implementations. No change needed; recording the assessment as the ticket asks.

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dream Skill: validate-drift

Generated: 2026-07-20T23:10:46+00:00
Command: `coga validate --json --fix`
Task: `decide-what-belongs-in-core-vs-skills-and-move-ski`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-20T23:15:39+00:00
Command: `coga validate --json --fix`
Task: `decide-what-belongs-in-core-vs-skills-and-move-ski`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-20T23:19:00+00:00
Command: `coga validate --json --fix`
Task: `decide-what-belongs-in-core-vs-skills-and-move-ski`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-20T23:23:14+00:00
Command: `coga validate --json --fix`
Task: `decide-what-belongs-in-core-vs-skills-and-move-ski`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-20T23:34:05+00:00
Command: `coga validate --json --fix`
Task: `decide-what-belongs-in-core-vs-skills-and-move-ski`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-20T23:35:40+00:00
Command: `coga validate --json --fix`
Task: `decide-what-belongs-in-core-vs-skills-and-move-ski`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
