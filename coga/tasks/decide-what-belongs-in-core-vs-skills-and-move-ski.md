---
slug: decide-what-belongs-in-core-vs-skills-and-move-ski
title: Decide what belongs in core vs skills and move skill-only recipes out of src
  coga
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
