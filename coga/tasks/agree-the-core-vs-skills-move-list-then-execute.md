---
slug: agree-the-core-vs-skills-move-list-then-execute
title: Agree the core-vs-skills move list then execute
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (design)
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
