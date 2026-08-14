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
  - coga/principles
  - coga/codebase
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

Make it possible for an ordinary ticket to execute as a script — deterministic
code, no LLM in the loop — rather than always composing a prompt and launching
an agent.

This is a microkernel enabler, not a convenience. Be precise about the gap:
deterministic code at the edge is already allowed — `CLAUDE.md` permits a
single-consumer helper to "live beside the ticket or skill that uses it […] and
be invoked explicitly by agent instructions." What does not exist is a way to
**execute** that code headlessly as a ticket, with no agent in the loop. Every
deterministic feature that needs a stable headless contract therefore has to
become a `runner.RECIPES` entry inside `src/coga/`. Close that gap and most
features can live as tickets at the edge; leave it open and the kernel only
grows. The `recipe:` field is the symptom that surfaced this, not the subject.

### What the design step must deliver

The `design` step writes a spec that states, at minimum:

- **Declaration surface** — frontmatter field, a step `assignee: script`, or
  something else. Per-ticket or per-step, and whether it may appear mid-workflow
  alongside agent steps.
- **Argv/env contract** — what the script receives. Note that `task_env.py`
  still supplies task *identity* (`COGA_TASK_*`, `COGA_REPO_ROOT`) to both agent
  and recipe paths, but the **argument channel is gone**: `apply_arg_env`,
  `COGA_ARG_1..N`, and `COGA_ARGC` lived in the deleted `launch_script.py` and
  have no replacement. If the shape takes arguments, that is new work.
- **Execution model** — headless vs TTY, and how `coga recurring`, `coga
  launch`, and the REPL supervisor each treat a script-backed ticket.
- **Lifecycle** — what `bump`, `block`, and blackboard writes mean when no agent
  is present to perform them.
- **Contract deltas** — the exact prose changes to `CLAUDE.md`, `AGENTS.md`, and
  the `coga/extension-model`, `coga/codebase`, `coga/architecture`, and
  `coga/recurring` contexts.
- **A quantified microkernel claim** — how many lines actually leave `src/coga/`
  under the proposal. Ten `RECIPES` entries are ten lines in a dict; the real
  code sits in `autoclose.py`, the digest module, and friends, much of which may
  be shared infra that stays either way. Without a number the argument is
  rhetorical and a defender of #670 will say moving dict entries shrinks nothing.

**A design that concludes the current contract should stand is an acceptable
outcome.** Say so plainly in the spec and stop at `review-design`; do not
manufacture a reversal to satisfy the ticket.

## Context

### Where this came from — `recipe:` (tracked separately, do not design it here)

`recipe:` on a recurring template is the script-vs-agent mode switch. A known
`recipe:` runs headlessly via `coga run <name>` as a subprocess
(`recurring_runner.py:698` branches, `:794` spawns); without one the task is
agent-backed and needs a TTY under the REPL supervisor.
`coga/contexts/coga/recurring/SKILL.md:120-122` states it directly: *"there is
no `mode` field. A known `recipe:` selects deterministic recipe execution."*
`Template.load` checks the name against the fixed registry
(`recurring.py:76-87`).

The field looks redundant against the one-step workflow each template also
carries, and that duplication is worth trimming — but it is a standalone
refactor of existing plumbing, decidable and shippable without this ticket. It
is **out of scope here**; see Out of Scope below.

The part that matters for *this* ticket is the boundary: `recipe:` exists only
on recurring templates. An ordinary ticket cannot execute as a script at all.
That gap is the subject.

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
microkernel backwards: it closed the only door out of core, so deterministic
behavior needing a headless contract can now only grow the kernel. The design
must engage #670's stated reasons — legibility, reviewability, no plugin host,
no recursive discovery — and either rebut them or show how the new shape
preserves what they protected. The strongest statement of the counter-case is
`coga/contexts/coga/architecture/SKILL.md:764-765`; read the surrounding section,
which is not attached to this ticket. `git show 755e60de` shows the full scrub:
25+ files across contexts, templates, README, `docs/vision.md`,
`docs/market-thesis.md`, `docs/concepts.md`, and `docs/reference.md`. A reversal
is at least as large a prose surface as a code change.

**Consider a middle path before treating this as binary.** One shape the owner
has not ruled on: keep `runner.RECIPES` as the explicit *dispatch* surface, but
let a recipe's implementation live beside its ticket through declarative
registration — no plugin host, no recursive discovery. That could satisfy every
stated reason for #670 *and* the microkernel goal without restoring `script:`.
If the design presents only reverse-or-don't, `review-design` degrades into a
yes/no vote.

### Current state of the ground — verified, and not what the log suggests

- **Nothing declares `script:` today.** The `coga/show` and `coga/ticket/finalize`
  twins were scrubbed in `755e60de` along with everything else. Blocker messages
  in `coga/log.md` naming them as survivors predate the merge and are stale. Do
  not go looking for a surviving example to model on.
- **`validate.py` is not an obstacle.** It has no `script` handling at all. The
  coverage added by #670 is `tests/test_validate.py:339`,
  `test_validate_tolerates_legacy_non_null_script_key`, which asserts *tolerance*
  — a leftover key degrades to a warning, not a failure. Roughly 20 legacy
  tickets still carry an inert `script: null` that `Ticket.parse` strips
  (`src/coga/ticket.py:72-78`). Making `script` meaningful again is mostly adding
  it to `CANONICAL_TICKET_KEYS` and dropping that migration pop.
- **`CLAUDE.md`'s microkernel rule says the opposite of this ticket:**
  *"Deterministic behavior that needs a stable headless command contract must be
  a fixed name in `runner.RECIPES`"* and *"core must never import from a ticket
  or skill directory."* If this lands, that rule and the matching contexts change
  in the same PR — the repo rule is that behavior changes update their context.
- **Packaged/live copies are out of sync for `digest`.** Five recurring
  templates are recipe-backed, but only four have a live `coga/workflows/`
  directory; `digest/post` exists solely at
  `src/coga/resources/templates/coga/bootstrap/workflows/digest/post.md`.
  CLAUDE.md requires keeping both copies in sync, so expect to touch both trees.

### Out of scope

- The `recipe:`/one-step-workflow duplication on recurring templates. It is a
  standalone refactor; give it its own ticket.
- Migrating the ten existing `runner.RECIPES` entries out of core. Land the
  capability and the contract change first.

### Sizing

`755e60de` — the mirror image of this change — was 25+ files. If the design
expects comparable reach, have it propose a split (capability plus tests first,
prose-contract sweep second) rather than putting 25 files behind one owner
review at the final `review` gate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
