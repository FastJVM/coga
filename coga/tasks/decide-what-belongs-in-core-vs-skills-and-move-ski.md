---
slug: decide-what-belongs-in-core-vs-skills-and-move-ski
title: Decide what belongs in core vs skills and move skill-only recipes out of src
  coga
status: draft
mode: agent
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
step: 1 (implement)
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

### Part 1 — decide the policy (do this first; it's the real deliverable)

Write the rule into `CLAUDE.md` and/or the `coga/codebase` context. The proposed
starting point (confirm or revise with the owner):

- **User-facing workflow recipes** (a `code/*` step a user runs, like open-pr)
  must be **self-contained skills** — deterministic logic in the skill dir
  beside `run.py`, not in `src/coga/`. Hackability: a user edits the skill, not
  the installed package.
- **Coga's own internal machinery** may stay in core: anything backing a **CLI
  command**, anything **shared by multiple consumers**, and (the open question)
  **coga-internal recurring maintenance** (sweeps, digest, reminders) that is
  tightly coupled to git-sync / task state and is not a user extension point.

The crux to decide: does the carve-out for "coga-internal recurring maintenance"
hold, or should those move out too for strict consistency?

### Part 2 — apply it

Move whatever the policy says shouldn't be in core into its skill dir (sibling
module beside `run.py`, imports only shared core infra), keep live + packaged
template copies in sync, move the tests, run the full suite.

## Context

Inventory of what backs each script skill (from investigation on 2026-07-06):

**Definitely core — do NOT move (back a command or shared):**
- `commands/digest.py` (`run_digest`) — backs the `coga digest` CLI command.
- `megalaunch.py` — backs the `coga megalaunch` command.
- `authoring.py` (`finalize_authored_from_env`) — also backs `coga ticket` /
  `coga project`.
- `autoclose.py` **parsers** (`parse_worktree_path`, `parse_branch_name`,
  `parse_pr_url`) — shared by the open-pr recipe and 2 other call sites.

**Skill-only recipes still in core — the candidates to move (all back
coga-internal recurring maintenance, no command, no other consumer):**
- `autoclose.py` `sweep_merged` / `GhError` — backs `coga/autoclose/sweep`.
- `blocker_reminders.py` (`remind_blocked_tasks`) — backs `coga/blockers/remind`.
- `branchsweep.py` (`sweep_branches`) — backs `coga/branch-sweep/sweep`.

**Already done (the precedent):** `code/open-pr` — recipe moved out of core in
PR #517.

Note the wrinkle for `sweep_merged`: it lives in `autoclose.py` alongside the
shared parsers, so moving it means splitting that module (parsers stay, sweep
goes to the skill) — decide whether that split is worth it or whether cohesion
argues to leave it.

<!-- coga:blackboard -->

## Notes

Not yet decided (this ticket decides it): whether coga-internal recurring
maintenance recipes (`sweep_merged`, `blocker_reminders`, `branchsweep`) move
out of core, or the carve-out lets them stay. Part 1 settles the rule; Part 2
executes whatever it implies.
