---
slug: move-open-pr-recipe-into-the-code-open-pr-skill-ke
title: Move open_pr recipe into the code open-pr skill; keep only parse_worktree_path
  in core
status: draft
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

PR #517 (branch `open-pr-script`, open) added the ~307-line open-PR recipe as
`src/coga/open_pr.py` in the **core package**, with the skill directory holding
only a thin 44-line `run.py` wrapper that imports `coga.open_pr.open_pr`. The
real logic therefore lives in the installed package, not in the skill file the
operator can edit.

That cuts against Principle #1 (Hackable): to change *how a PR gets opened* you
edit the package, not `coga/skills/code/open-pr/`. A skill should be
self-contained in its directory.

**Goal:** make `code/open-pr` self-contained. Move the recipe into
`coga/skills/code/open-pr/` (a module beside `run.py`, or inlined into `run.py`),
and keep **only** the genuinely shared atom — `parse_worktree_path` — in core.

Scope:

1. Move the `open_pr()` recipe + `OpenPrError` out of `src/coga/open_pr.py` into
   the skill directory. Delete `src/coga/open_pr.py` (and its packaged template
   copy) once nothing imports it.
2. Keep `parse_worktree_path` in `src/coga/autoclose.py` (it is already the
   shared `## Dev` parser used by autoclose too) and have the skill import that
   one function from core.
3. Update `run.py` to load the recipe from the skill dir. **Verify first** that a
   script-step `run.py` can import a sibling module (does `launch_script` put the
   skill dir on `sys.path`?). If not, inline the recipe into `run.py`.
4. Move `tests/test_open_pr.py` coverage accordingly (it currently imports
   `from coga.open_pr import ...`) — the recipe must stay unit-testable from its
   new home.
5. Keep the live copy (`coga/skills/code/open-pr/`) and packaged template copy
   (`src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/`) in sync
   — there is a test enforcing this.

## Context

- **Depends on PR #517.** The code being refactored only exists on branch
  `open-pr-script`; it is not on `main`. Decide with the owner: **fold this into
  #517 before it merges** (cleaner — no churn landing on `main` then rewriting
  it), or land as a true follow-up after #517 merges. Folding-in is the
  recommended default.
- **Precedent to weigh, not blindly follow.** `src/coga/autoclose.py` and the
  digest flush use the *same* core-module-backs-a-script-skill pattern that #517
  copied. If "skills are self-contained" is the rule, those are the same
  question — but generalizing to them is **out of scope** here unless the owner
  asks for it. This ticket only moves `open_pr`.
- Motivating design discussion: Principle #7 (`coga/principles`, just added) and
  the antipattern of task/skill logic accreting into the core package.

<!-- coga:blackboard -->

## Decision (2026-07-06)

Folding the refactor **into PR #517** (branch `open-pr-script`), not launching
this ticket's own workflow — the code being refactored only exists on that
branch, not on `main`, so a fresh `code/with-review` launch off `main` would
have nothing to edit. If #517 merges with the refactor included, close this
ticket `done`.

## Feasibility findings

- **Sibling import works.** `build_script_command` runs a `.py` script step as
  `[sys.executable, run.py]`, so Python puts the script's own dir on
  `sys.path[0]`. `run.py` can therefore `import recipe` from the skill dir —
  true for both the live copy and the packaged-template copy (each ships its own
  `recipe.py`). No `sys.path` plumbing needed in `launch_script`.
- **"Keep only parse_worktree_path in core" was loose wording.** The recipe
  legitimately imports ~6 core modules (`autoclose` parsers, `compose`,
  `config`, `taskfile`, `ticket`, `github_preflight`) — shared infra, not
  task-specific logic, so they stay in core. What moves out of `src/coga/` is
  the *orchestration function* (`open_pr` / `OpenPrError` / `set_dev_pr`), into
  `coga/skills/code/open-pr/recipe.py`.
- **Only two importers** of `coga.open_pr`: the skill's `run.py` and
  `tests/test_open_pr.py`. `run.py` → `from recipe import ...`; the test loads
  `recipe` from the live skill dir via a `sys.path` insert.
- **Cost:** the recipe is no longer importable as a package module, so its unit
  test imports from the skill dir. Acceptable, but it's the real tradeoff of
  self-containment — the test now knows the skill's on-disk location.

## Status

**Done — folded into PR #517.** Commit `68b8b1a0` ("open-pr: move recipe into
the skill dir so the skill is self-contained") pushed to branch `open-pr-script`
on 2026-07-06. Changes:

- `src/coga/open_pr.py` → `coga/skills/code/open-pr/recipe.py` (git rename; core
  module removed).
- Added `recipe.py` to the packaged template skill dir; both `run.py` copies now
  `from recipe import ...`.
- `tests/test_open_pr.py` loads `recipe` from the skill dir via a `sys.path`
  insert; `tests/test_packaging.py` manifest now lists `open-pr/run.py` +
  `open-pr/recipe.py`.
- Full suite: 1090 passed, 1 skipped (`python3.12`).

When #517 merges, mark this ticket `done`. Not yet decided: whether to apply the
same self-containment move to `autoclose.py` / digest (left out of scope).
