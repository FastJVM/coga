---
slug: recurring-recipe-question
title: Deduce whether a ticket is a script or an agent prompt
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
code, no LLM required — instead of every ticket composing a prompt and launching
an agent. Not either/or: a ticket may be script-only, agent-only, or a script
that runs first and hands off to an agent.

This is a microkernel enabler, not a convenience. Be precise about the gap:
deterministic code at the edge is already allowed — `CLAUDE.md` permits a
single-consumer helper to "live beside the ticket or skill that uses it […] and
be invoked explicitly by agent instructions." What does not exist is a way to
**execute** that code headlessly as a ticket, with no agent in the loop. Every
deterministic feature that needs a stable headless contract therefore has to
become a `runner.RECIPES` entry inside `src/coga/`. Close that gap and most
features can live as tickets at the edge; leave it open and the kernel only
grows.

### No new declaration field — deduce the type

The owner's requirement, and a hard constraint on the design: **do not add a
mode field.** Not `script:`, not a revived `recipe:`, not `assignee: script`. A
ticket is already either a script or an agent prompt, and that is obvious from
what is sitting next to it. The one piece of code this ticket needs is a
classifier at launch that decides which, and dispatches.

The rule, as the owner specified it. Two independent questions, three outcomes:

| script in the directory? | ticket has work for an agent? | launch          |
| ------------------------ | ----------------------------- | --------------- |
| yes                      | no — body is only context     | script alone    |
| no                       | yes                           | agent alone     |
| yes                      | yes                           | **script, then agent** |

The third row is the point, and it is why this is not a binary switch. A script
ticket is not necessarily a *replacement* for an agent — the script can run
first as a deterministic preparation step and the agent run after it, with the
script's work already done. Most of the value of "tickets can be scripts" comes
from this row: the deterministic part stops being something an LLM does badly
and slowly, without giving up the agent for the part that needs judgment.

There is an existing mechanism for handing the script's output to the agent, and
the design should use it rather than invent a channel: **the blackboard is
already a composed prompt layer.** A script that appends its findings to the
blackboard is automatically feeding the agent that follows it, with no new
plumbing and with the handoff visible in git. That is the same contract recipes
already follow (`task_env.py` hands them `COGA_TASK_BLACKBOARD`).

`recipe:` is then not a thing to trim — it is a thing that stops existing once
the classifier can deduce the same fact. It goes in this ticket; see *"Deleting
`recipe:` is a format change, not a migration"* under Context for why that costs
no implementation moves.

### What the design step must deliver

The `design` step writes a spec that states, at minimum:

- **The two signals, and how each is read.** "Is there a script here" is the
  easy one — settle the entry-point name, whether the executable bit counts, and
  what happens with more than one candidate or a non-executable `run.py`.

  **"Does this ticket have work for an agent" is the hard one, and it is where
  deduction can quietly turn back into guessing.** "The body is just context"
  must be decidable structurally — by `ls`, by section shape, by whether the
  current workflow step carries agent skills — and never by reading the prose
  and judging its intent, which would need an LLM to decide whether to launch an
  LLM. The current workflow step looks like the strongest candidate: a step with
  `skills:` and `assignee: agent` wants an agent, one without does not, and that
  is already declared, already frozen, and already validated. Whatever the design
  picks, state the rule so a human can predict the outcome from the directory
  without running anything.

  A wrong guess here is worse than the field this replaces: silently skipping
  the agent half of row three does the deterministic work and then stops, which
  looks like success. Say what makes that loud.
- **Where the classifier lives** — one function, called by `coga launch` and by
  the recurring runner, so both paths deduce identically rather than keeping two
  notions of "what kind of thing is this."
- **Argv/env contract** — what the script receives. Note that `task_env.py`
  still supplies task *identity* (`COGA_TASK_*`, `COGA_REPO_ROOT`) to both agent
  and recipe paths, but the **argument channel is gone**: `apply_arg_env`,
  `COGA_ARG_1..N`, and `COGA_ARGC` lived in the deleted `launch_script.py` and
  have no replacement. If the shape takes arguments, that is new work.
- **Execution model** — headless vs TTY, and how `coga recurring`, `coga
  launch`, and the REPL supervisor each treat a script-backed ticket. Row three
  is mixed: the script half is headless, the agent half may need a TTY. Say what
  a TTY-less environment does with a row-three ticket — run the script and skip
  the agent with a warning, as recurring already does for agent templates, or
  refuse the whole thing.
- **Failure semantics for row three** — what a non-zero script exit means for
  the agent that was going to follow. Halting is the obvious default; say so and
  say how the ticket reports it, rather than leaving it to the implementation.
- **Lifecycle** — what `bump`, `block`, and blackboard writes mean when no agent
  is present to perform them. In row three, which half is responsible for the
  bump — almost certainly the agent, since the script is a preparation step and
  not the end of the work.
- **Contract deltas** — the exact prose changes to `CLAUDE.md`, `AGENTS.md`, and
  the `coga/extension-model`, `coga/codebase`, `coga/architecture`, and
  `coga/recurring` contexts.
- **An honest microkernel claim.** No implementation leaves `src/coga/` in this
  ticket, so do not claim a shrink that has not happened. The
  claim to defend is narrower and checkable: a new deterministic feature can now
  ship entirely at the edge without touching core. Demonstrate it — describe the
  smallest end-to-end example of a feature that would previously have required a
  `runner.RECIPES` entry and now does not.

**A design that concludes the current contract should stand is an acceptable
outcome.** Say so plainly in the spec and stop at `review-design`; do not
manufacture a reversal to satisfy the ticket.

## Context

### The `recipe:` field this replaces

`recipe:` on a recurring template is today's script-vs-agent mode switch. A
known `recipe:` runs headlessly via `coga run <name>` as a subprocess
(`recurring_runner.py:698` branches, `:794` spawns); without one the task is
agent-backed and needs a TTY under the REPL supervisor.
`coga/contexts/coga/recurring/SKILL.md:120-122` states it directly: *"there is
no `mode` field. A known `recipe:` selects deterministic recipe execution."*
`Template.load` checks the name against the fixed registry
(`recurring.py:76-87`).

Two things are wrong with it. It exists **only on recurring templates**, so an
ordinary ticket cannot execute as a script at all. And it is a declaration of
something already visible: five recipe-backed templates each state their nature
three times over — `recipe:`, a one-step `workflow:` that exists only to name
the matching skill, and that step's `assignee: agent`, which is false because no
agent runs it. All five carry a comment conceding the point: *"The one-step
workflow keeps the period task's lifecycle and skill contract legible."*

A classifier that deduces the type makes `recipe:` redundant rather than merely
duplicated. That is the intended end state.

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

**Deduction collides head-on with #670's central objection — this is the crux.**
#670's stated reason was *"no plugin host, no recursive discovery"*, and
`coga/architecture` extends it to Dream: *"Dropping a SKILL.md under
`bootstrap/dream/tasks/` does not enable it; there is no recursive discovery, no
registry, and no daemon."* A classifier that reads file presence is, literally,
a file appearing in a directory changing behavior. The design cannot route
around this; it has to meet it.

The available rebuttal, which the design should either make properly or reject:
this is not repo-wide plugin discovery. It is one entry point inside one
ticket's own directory, listed by `ls`, affecting only that ticket, with no
registry to consult and nothing enabled anywhere else. "Discovery" in #670's
sense meant scanning a tree to find capabilities the system would then offer;
this scans nothing. If that distinction holds, the contracts can be rewritten to
permit it without reopening the plugin-host door. If it does not hold, say so —
that is a legitimate design outcome.

A middle path also exists and should be weighed rather than skipped: keep
`runner.RECIPES` as an explicit *dispatch* surface while implementations live
beside their tickets via declarative registration. It satisfies #670's reasons
but keeps a declaration, so it only partly meets the no-new-field constraint.
Present it as the fallback if deduction cannot be defended.

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
  (`src/coga/ticket.py:72-78`). Under the no-new-field constraint these stay
  inert and can simply be scrubbed; the classifier needs no frontmatter support,
  so `CANONICAL_TICKET_KEYS` should not grow. Validation work is the opposite
  shape: warn on a ticket whose directory looks script-like but whose entry point
  is unrunnable, since that is the failure deduction introduces.
- **`CLAUDE.md`'s microkernel rule says the opposite of this ticket:**
  *"Deterministic behavior that needs a stable headless command contract must be
  a fixed name in `runner.RECIPES`"* and *"core must never import from a ticket
  or skill directory."* If this lands, that rule and the matching contexts change
  in the same PR — the repo rule is that behavior changes update their context.
  Note the second clause may survive intact: a classifier *subprocesses* an
  entry point, it does not import it, so core still never imports from a ticket
  directory. Worth stating explicitly in the rewrite rather than leaving the
  reader to infer it.
- **Packaged/live copies are out of sync for `digest`.** Five recurring
  templates are recipe-backed, but only four have a live `coga/workflows/`
  directory; `digest/post` exists solely at
  `src/coga/resources/templates/coga/bootstrap/workflows/digest/post.md`.
  CLAUDE.md requires keeping both copies in sync, so expect to touch both trees.

### Deleting `recipe:` is a format change, not a migration

It looks at first like `recipe:` cannot be deduced away until the ten
`runner.RECIPES` implementations move out of `src/coga/`: `recipe: autoclose`
names an entry in a core registry, and there is no file beside
`coga/recurring/autoclose-merged/ticket.md` for a classifier to find. That
framing is wrong, and the design should not adopt it.

**Only the template format has to change.** Give each recurring template the
entry point it currently lacks — a thin script beside its `ticket.md` that
imports the core function and calls it. The classifier then finds a file exactly
as it does for any other script ticket, and `recipe:` can be deleted in the same
change. No implementation moves.

This is the edge shape `CLAUDE.md` already sanctions: *"A single-consumer helper
may live beside the ticket or skill that uses it, import only shared core infra,
and be invoked explicitly by agent instructions."* A shim that imports
`coga.autoclose` is precisely that. The dependency arrow stays correct — the
shim imports core; core never imports the shim — so the *"core must never import
from a ticket or skill directory"* rule is untouched.

The consequence worth stating plainly: **the capability and the migration are
now independent.** This ticket lands the classifier, the template format change,
and the deletion of `recipe:`. Whether a given implementation later moves out of
`src/coga/` becomes an ordinary per-job judgment about whether that code is
still shared infra — decided one job at a time, with no further format change,
and never as a precondition for anything here.

The design should still say what the shim looks like concretely (one per
template, or one shared dispatcher), and whether the ten `runner.RECIPES`
entries and `coga run` survive as a public command surface once nothing in
`coga/recurring/` depends on them.

### Out of scope

- Migrating the ten recipe implementations out of `src/coga/`. Decoupled by the
  format change above; each is its own later judgment call.
- Rewriting the implementations themselves. Behavior changes to `autoclose`,
  `digest`, and friends belong in their own tickets.

### Sizing

The code half is small — a classifier, a dispatch branch in two call sites, one
shim per recurring template, and the `recipe:` deletion. The prose half is not:
`755e60de`, the mirror image of this change, touched 25+ files across contexts,
templates, README, `docs/vision.md`, `docs/market-thesis.md`, `docs/concepts.md`,
and `docs/reference.md`, and every one of those statements has to be re-examined.

If the design expects that reach, have it propose a split — capability plus
tests first, prose-contract sweep second — rather than putting 25+ files behind
one owner review at the final `review` gate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
