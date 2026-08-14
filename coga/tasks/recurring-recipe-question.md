---
slug: recurring-recipe-question
title: Let an ordinary ticket execute as a script
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/extension-model
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

Make it possible for an ordinary ticket to execute as a script — deterministic
code, no LLM in the loop — rather than always composing a prompt and launching
an agent.

This is a microkernel enabler, not a convenience. Today the only home for
deterministic Coga behavior is `runner.RECIPES` inside `src/coga/`, so every new
deterministic feature makes the kernel bigger. If a ticket can be a script, most
features can live as tickets at the edge and the kernel can shrink to genuine
shared infra. That is the goal to design against; the `recipe:` field below is
the symptom that surfaced it.

Design the shape first (this ticket's `design` step), get owner sign-off at
`review-design`, then implement. The design must take a position on the
reversal described under Context — it is not free to assume the current
contract.

## Context

### The `recipe:` observation that started this

`recipe:` on a recurring template is the script-vs-agent mode switch. A known
`recipe:` runs headlessly via `coga run <name>` as a subprocess
(`recurring_runner.py:698`); without one the task is agent-backed and needs a
TTY under the REPL supervisor. `coga/contexts/coga/recurring/SKILL.md` states it
directly: *"there is no `mode` field. A known `recipe:` selects deterministic
recipe execution."* Validation checks the name against the fixed registry
(`recurring.py:76-95`).

The field is arguably redundant, and the duplication is real but not where it
first appears. `coga/recurring/autoclose-merged/ticket.md` declares the same
fact three times: `recipe: autoclose`; `workflow: autoclose-merged/sweep`, a
one-step workflow whose only purpose is to name the skill `coga/autoclose/sweep`;
and that step's `assignee: agent`, which is false — no agent runs it. All four
recipe-backed templates carry the same comment conceding the point: *"The
one-step workflow keeps the period task's lifecycle and skill contract
legible."*

Two opposite trims are available and the design should say which it takes, or
that neither matters once tickets can be scripts:

1. Drop `recipe:` and deduce it — from the template directory name (needs
   renaming `autoclose-merged` → `autoclose`) or from the workflow step's skill
   ref. Both trade an explicit field for an implicit convention coupling a
   template name to the Python registry.
2. Drop the one-step workflow instead and keep `recipe:` as the single honest
   declaration. Removes four workflow files and the false `assignee: agent`.

Either way, `recipe:` exists **only on recurring templates**. An ordinary ticket
cannot be a script at all. That gap is this ticket.

### This reverses a recently merged decision — read before designing

The capability being asked for existed and was deliberately removed. A ticket
could declare `script: run.py` in frontmatter, and `launch_script.py` /
`build_script_command` executed it with `COGA_ARG_1` / `COGA_ARGC` in the
environment. The three-ticket `remove-run-py/` epic deleted it:

- `remove-run-py/add-coga-run-generic-runner-and-migrate-recurring` (PR #650)
- `remove-run-py/port-hard-consumers-onto-the-generic-runner` (PR #667)
- `remove-run-py/delete-the-script-seam` (PR #670) — commit `755e60de`

PR #670 rewrote the contracts to forbid it. `coga/extension-model` (attached)
now reads: *"Command tickets always compose a prompt and launch an agent.
Deterministic behavior with a stable Coga command contract belongs in
`runner.RECIPES`."* Its three-homes list was edited from "skills and script
steps running on a ticket" to "agent steps and skills running on a ticket."
`coga/architecture` adds: *"Keeping the registry explicit makes the available
code legible and reviewable; installed skills are process contracts, not
executable plugins."*

**Do not treat that as settled.** The owner's position is that #670 got the
microkernel backwards: it moved deterministic logic *into* core — ten entries in
`runner.RECIPES` — and closed the only door out, which grows the kernel rather
than shrinking it. The design step must engage the stated reasons for #670
(legibility, reviewability, no plugin host, no recursive discovery) and either
rebut them or show how the new shape preserves what they were protecting. Read
`git show 755e60de` for the full scope of what was scrubbed; it touched contexts,
templates, README, vision, and the market thesis, so a reversal is a large
prose surface as well as a code change.

### Constraints from the current contract

- `CLAUDE.md`'s microkernel rule currently says the opposite of this ticket:
  *"Deterministic behavior that needs a stable headless command contract must be
  a fixed name in `runner.RECIPES`"* and *"core must never import from a ticket
  or skill directory."* If this lands, that rule and the matching contexts
  change in the same PR — the repo rule is that behavior changes update their
  context.
- Two vestigial `script:` declarers survived the scrub as twins: `coga/show` and
  `coga/ticket/finalize`. `validate.py` gained coverage rejecting a leftover
  non-null `script:` key — that check is a direct obstacle and will need
  revisiting.
- `task_env.py` already builds the shared `COGA_TASK_*` contract for both agent
  launches and recipe subprocesses, so the env-passing half of this likely
  exists already.

### Out of scope

Migrating the ten existing `runner.RECIPES` entries out of core. Land the
capability and the contract change first; moving live jobs is follow-up work.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
