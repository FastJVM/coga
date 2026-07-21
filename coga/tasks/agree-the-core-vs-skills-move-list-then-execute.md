---
slug: agree-the-core-vs-skills-move-list-then-execute
title: Agree the core-vs-skills move list then execute
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

Restaged from `decide-what-belongs-in-core-vs-skills-and-move-ski` (PR #618,
closed unmerged for process reasons — the owner wants explicit agreement on
scope before execution, not after). The microkernel policy itself is decided
(owner, 2026-07-17) and unchanged: core (`src/coga/`) holds only genuine
shared infra (≥2 real consumers) and real command implementations; everything
else lives with its skill, fronted by an alias/bootstrap target when it needs
a command surface.

This ticket re-runs the *application* of that policy in agreed stages:

### design step — produce the list and the plan (no code changes)

Write into this ticket, for owner review:

1. **The move list** — every `src/coga/` module/symbol the policy says must
   leave core, one line each: what it is, where it goes, what (if anything)
   stays behind as shared infra. Start from the 2026-07-06 inventory (see
   Context) and re-verify it against current `main` — consumers may have
   changed since.
2. **The ticket plan** — how the moves land: one ticket per move (or a
   justified grouping), each with its own test plan (what proves the move is
   behavior-neutral: repointed tests, packaging coverage, live↔packaged sync
   guards, script-launch smoke).
3. **Borderline calls** — anything the alias test leaves ambiguous (last
   round: `coga digest`, `coga megalaunch` — both assessed as legitimately
   core), stated with a recommendation each so the owner can rule.

Do not write or move any code in this step.

### review-design step — owner agrees

Owner prunes/edits the list and the ticket plan directly in this file, rules
on borderline calls, then bumps. Nothing executes before this bump.

### implement onward — execute the agreed plan

Execute exactly the agreed list — either in this ticket or by scaffolding the
agreed child tickets, per what review-design settled. **Reuse, don't redo:**
the closed PR's branch `microkernel-move-recipes` (worktree
`../coga-microkernel-move-recipes`) already contains a full, peer-reviewed,
green implementation of the three-recipe move (autoclose sweep, blocker
reminders, branch sweep) plus the policy docs. Rebase/cherry-pick from it for
whatever survives the agreed list; drop what doesn't.

## Context

Prior art and inputs:

- **Closed PR:** https://github.com/FastJVM/coga/pull/618 — full
  implementation, closed for restaging, branch preserved.
- **Policy text** already exists on that branch for `CLAUDE.md` / `AGENTS.md`
  and the `coga/codebase` context ("microkernel rule").
- **2026-07-06 inventory** (from the original ticket, re-verify against main):
  - Stays core (shared infra): `authoring.py` (`finalize_authored_from_env`);
    `autoclose.py` parsers (`parse_worktree_path`, `parse_branch_name`,
    `parse_pr_url`) plus `GhError` / `pr_state` (consumers: `branchcleanup` →
    `retire`, branch-sweep recipe, Dream orphan-marker).
  - Move candidates (single-consumer recurring maintenance):
    `autoclose.py::sweep_merged` + sweep helpers → `coga/autoclose/sweep`;
    `blocker_reminders.py` → `coga/blockers/remind`; `branchsweep.py` →
    `coga/branch-sweep/sweep`.
  - Borderline (real command vs alias): `commands/digest.py` (`run_digest`),
    `megalaunch.py` — last assessment: both genuinely core.
- **Precedent:** PR #517 moved `open_pr.py` to the `code/open-pr` skill;
  PR #585 later made open-pr a genuine core command again — use as a caution
  when classifying.
- **Follow-up ticket (separate, unchanged):**
  `rewrite-coga-base-prompt-and-agent-mode-block`, sequenced after this.

## Move list (re-verified against main, 2026-07-21)

The 2026-07-06 inventory holds unchanged. Consumers re-checked by grep on
current `main`; a fresh sweep of every other `src/coga/` module found no new
single-consumer candidates — everything else either has ≥2 real consumers or
is a real command implementation.

**Moves (3):**

1. **`autoclose.py::sweep_merged` + sweep-only helpers** (`_try_bump_one`,
   `_on_final_step`, `_candidate`, `_read_pr_url`; ~154 lines) →
   `coga/autoclose/sweep` skill `recipe.py`. Sole consumer on main is that
   skill's `run.py` (live + packaged copies, already in sync); the `autoclose`
   command surface is already a default alias (`recurring launch
   autoclose-merged`), no import. **Stays behind in `src/coga/autoclose.py`
   as shared infra:** `GhError`, `pr_state`, `parse_pr_url`,
   `parse_branch_name`, `parse_worktree_path`, `parse_pr_number` — consumers:
   `open_pr.py`, `branchcleanup.py` (→ `coga retire`), `step_gate.py` (the
   `pr` gate), and the branch-sweep recipe.
2. **`blocker_reminders.py`** (whole module, `remind_blocked_tasks`,
   183 lines) → `coga/blockers/remind` skill `recipe.py`. Sole consumer is
   that skill's `run.py`. Nothing stays behind.
3. **`branchsweep.py`** (whole module, `sweep_branches`, 270 lines) →
   `coga/branch-sweep/sweep` skill `recipe.py`. Sole consumer is that skill's
   `run.py`. Nothing stays behind; the recipe keeps importing `GhError` /
   `parse_branch_name` from core `coga.autoclose` (shared infra, per policy).

**Verified stays-core (unchanged from inventory):** `authoring.py`
(consumers: `commands/ticket.py`, `megalaunch.py`, `coga/ticket/finalize`
skill via `finalize_authored_from_env`); the `autoclose.py` parser/`pr_state`
block above. Modules newly re-checked and confirmed core: `views.py`
(show + status commands + `coga/show` skill), `delete_task.py` (`coga delete`
+ `recurring.py`), `open_pr.py` (real command since PR #585), `spool.py`,
`period_state.py`, `github_source.py`, `github_preflight.py`, `usage.py`,
`recurring_runner.py` — all ≥2 consumers or real command implementations.

## Ticket plan

**Recommended: one grouped execution, in this ticket, no child tickets.**
The three moves are the same mechanical shape (relocate single-consumer
recipe logic into its skill dir, repoint `run.py`), they share the policy-doc
changes, and a full peer-reviewed green implementation already exists on
`microkernel-move-recipes` (worktree `../coga-microkernel-move-recipes`).
Verified: `main` has **zero drift** since the merge-base on every file the
branch touches (`autoclose.py`, `blocker_reminders.py`, `branchsweep.py`,
`branchcleanup.py`, the six live/packaged skill dirs, the three recurring
templates, the repointed tests, CLAUDE.md/AGENTS.md, the codebase context) —
the branch rebases clean. Splitting into three child tickets would re-stage
three PRs of overhead for a diff that already passed review ("reuse, don't
redo").

Test plan (one PR, all four legs — all already present on the branch):

- **Repointed tests** — moved-logic tests load the skill-local `recipe.py`
  (branch adds a `tests/conftest.py` recipe-loading helper);
  `test_autoclose.py` keeps covering the parsers that stay core.
- **Packaging coverage** — `test_packaging.py` additions assert the
  `recipe.py` files ship in the wheel (guards the pure-data-dir force-include
  gotcha).
- **Live↔packaged sync** — both `coga/skills/coga/...` and
  `bootstrap/skills/coga/...` copies updated in the same PR, kept identical.
- **Script-launch smoke** — each recipe runs end-to-end through the script
  step path (`coga recurring launch <name> --force` or equivalent), plus
  `python -m pytest` and `coga validate --json`.

## Borderline calls

- **`coga digest` (`commands/digest.py::run_digest`) — recommend: stays
  core.** Real registered command, and genuinely ≥2 consumers: the CLI head
  and the `coga/digest/flush` skill `run.py`, which imports `run_digest`
  directly. The alias test doesn't apply — there's a real command behind it.
- **`coga megalaunch` (`megalaunch.py` + `commands/megalaunch.py`) —
  recommend: stays core.** Real interactive command (plus the `pick` default
  alias), imports authoring/recurring-runner internals, and the reverse move
  was already tried and rolled back: `coga/megalaunch/run` sits in
  `paths.py`'s removed-bundled-skill registry ("megalaunch is now on-demand
  only"). Same caution as the open-pr precedent (#517 → #585).

## Owner ruling (review-design, 2026-07-21)

1. **Grouping:** one PR in this ticket, rebasing the peer-reviewed
   `microkernel-move-recipes` branch. No child tickets.
2. **Policy docs ride along** in the same PR.
3. **Borderlines:** `digest` and `megalaunch` stay core as recommended.
   `open-pr` stays core **in this ticket**, but its long-term shape is
   deliberately unsettled: the owner wants it re-attempted as the pilot for a
   general "commands as tickets" direction (argument channel for launch
   targets, nested-launch rules, blackboard write ownership). That work is
   staged separately in draft ticket `commands-as-tickets-open-pr-pilot`
   (owner will launch and co-design). The #585 caution stands until that
   pilot concludes; nothing about it changes this ticket's diff.

## Acceptance Criteria

- [ ] `src/coga/blocker_reminders.py` and `src/coga/branchsweep.py` no longer
  exist; `src/coga/autoclose.py` retains only `GhError`, `pr_state`, and the
  four parsers (plus their regexes).
- [ ] Each of the three skills owns its logic as a `recipe.py` beside
  `run.py`, identical in live `coga/skills/` and packaged
  `bootstrap/skills/`, and `run.py` imports the recipe, not `coga.<module>`.
- [ ] Command surfaces unchanged: `autoclose` alias, the three recurring
  templates, and their workflows still launch and pass the script-step path.
- [ ] Microkernel policy text landed in CLAUDE.md, AGENTS.md, and the
  `coga/codebase` context.
- [ ] `python -m pytest` green (including the new packaging + repointed
  tests); `coga validate --json` clean for this task.

## Out of Scope

- Moving `coga digest`, `coga megalaunch`, or `open_pr.py` (ruled core in
  review-design; open-pr's future is delegated to the separate
  `commands-as-tickets-open-pr-pilot` draft).
- The base-prompt rewrite — separate follow-up ticket
  `rewrite-coga-base-prompt-and-agent-mode-block`.
- Any behavior change to the three recipes themselves (schedules, output,
  Slack posts) — this is a relocation, behavior-neutral by test plan.
- New skills, new commands, or touching the other `coga/skills/coga/*`
  wrappers (`show`, `digest/flush`, `ticket/finalize`).

<!-- coga:blackboard -->

## Design step notes (2026-07-21)

Re-verified the 2026-07-06 inventory against main by grepping consumers of
every candidate module; results written into the ticket body (Move list /
Ticket plan / Borderline calls / Acceptance Criteria / Out of Scope). Key
facts an implementer should not re-derive:

- Merge-base of `main`..`microkernel-move-recipes` is `b6e004be`; `git diff
  --stat <mb>..main` over every branch-touched file is **empty** — the branch
  rebases onto main with no conflicts expected. Worktree still exists at
  `../coga-microkernel-move-recipes` (2 commits: `95c427e5` move,
  `9c1ddb00` peer-review fixes).
- The three skill `run.py` wrappers already exist on main (live + packaged,
  in sync) but still import core (`coga.autoclose` / `coga.blocker_reminders`
  / `coga.branchsweep`) — the branch is what flips them to skill-local
  `recipe.py` (git renames R092/R095, so history follows).
- Fresh sweep of remaining `src/coga/` modules found no additional
  single-consumer candidates (checked: views, delete_task, open_pr, spool,
  period_state, github_source, github_preflight, usage, recurring_runner,
  slack_response — all ≥2 consumers or real commands).

## Open Questions — resolved (owner, 2026-07-21)

All three resolved in the ticket body's `## Owner ruling` section: one PR in
this ticket (rebase `microkernel-move-recipes`), policy docs ride along,
digest/megalaunch/open-pr all stay core. open-pr's re-examination is staged
as draft `commands-as-tickets-open-pr-pilot` (owner will launch + co-design);
it does not touch this ticket's diff. Nothing pending — implement step
executes the agreed plan as written.
