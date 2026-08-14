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
grows.

### No new declaration field — deduce the type

The owner's requirement, and a hard constraint on the design: **do not add a
mode field.** Not `script:`, not a revived `recipe:`, not `assignee: script`. A
ticket is already either a script or an agent prompt, and that is obvious from
what is sitting next to it. The one piece of code this ticket needs is a
classifier at launch that decides which, and dispatches.

The leading candidate is **file presence**: a directory-form ticket
(`tasks/<slug>/`) with an executable entry point beside `ticket.md` is a script
ticket; without one it composes a prompt and launches an agent. The design
confirms or replaces that signal, but the no-new-field constraint holds either
way.

`recipe:` is then not a thing to trim — it is a thing that stops existing once
the classifier can deduce the same fact. See Sequencing below for how far this
ticket carries that.

### What the design step must deliver

The `design` step writes a spec that states, at minimum:

- **The deduction rule** — the exact signal the classifier reads, in priority
  order, and what it does when signals conflict or are ambiguous (an executable
  beside a ticket whose body also reads like a prompt; a non-executable
  `run.py`; more than one candidate entry point). Deduction that guesses wrong
  silently is worse than a field; the rule must be decidable by `ls` and by a
  human reading the directory.
- **Where the classifier lives** — one function, called by `coga launch` and by
  the recurring runner, so both paths deduce identically rather than keeping two
  notions of "what kind of thing is this."
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

### Sequencing — how far this ticket goes

Deleting `recipe:` and migrating the ten `runner.RECIPES` entries are the same
move, and that is a sequencing problem the design must resolve explicitly.

A recurring template's `recipe: autoclose` points at a *name in a core
registry*, not at code beside the template. There is no file next to
`coga/recurring/autoclose-merged/ticket.md` for a classifier to find. So
`recipe:` cannot be deduced away until that job's implementation moves out of
`src/coga/` to sit beside its ticket — which is the migration. The two cannot be
separated by wishing.

The design picks one and justifies it:

- **Capability first.** Land the classifier and the contract change; ordinary
  tickets gain script execution; `recipe:` survives on recurring templates until
  a follow-up migrates the jobs. Smaller and reviewable, but leaves two
  mechanisms live at once, which is the state this ticket is complaining about.
- **One job as proof.** Land the classifier and migrate exactly one recipe
  (`autoclose` is the smallest) to prove the path end to end, deleting its
  `recipe:` and its one-step workflow. Leaves nine behind but demonstrates the
  end state rather than asserting it.
- **Full migration.** All ten, `recipe:` deleted outright. Cleanest end state,
  almost certainly too large for one review given #670's mirror-image change was
  25+ files.

Recommendation to weigh, not a decision: the middle option. The owner decides at
`review-design`.

### Out of scope

Rewriting the ten recipe *implementations* themselves. Whatever migrates moves
as-is; behavior changes to `autoclose`, `digest`, and friends belong in their
own tickets.

### Sizing

`755e60de` — the mirror image of this change — was 25+ files. If the design
expects comparable reach, have it propose a split (capability plus tests first,
prose-contract sweep second) rather than putting 25 files behind one owner
review at the final `review` gate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

An independent session read the ticket cold and fact-checked it against the
repo. Its four factual corrections have already been applied to `## Context`;
the review is kept here verbatim until the ticket is approved.

---

# Independent review — `recurring-recipe-question`

## Factual check against the repo

**Confirmed accurate:**

- `recurring_runner.py:698` — exactly `if task.recipe:`. (The subprocess itself is at `:794`, `[sys.executable, "-m", "coga.cli", "run", task.recipe]` — worth citing both, since 698 is only the branch.)
- `coga/contexts/coga/recurring/SKILL.md:120-122` — quote is verbatim.
- `runner.RECIPES` has exactly ten entries: `autoclose, digest, blocker-reminders, branch-sweep, validate-drift, cleanup-orphan-markers, recurring-scan, skill-update, open-pr, delete-task`.
- PRs #650 (`2a26d9df`), #667 (`f6522603`), #670 (`755e60de`) all exist under those slugs; `755e60de` is `Delete the script-seam (#670)`, 2026-07-29.
- `src/coga/commands/launch_script.py` (492 lines) with `build_script_command` at `:97` and `COGA_ARG_1`/`COGA_ARGC` — deleted in `755e60de`. Accurate.
- `coga/contexts/coga/extension-model/SKILL.md:101-102` quote — verbatim. The three-homes edit is verbatim too: *"expressed as skills and script steps running on a ticket"* → *"expressed as agent steps and skills running on a ticket."*
- `coga/contexts/coga/architecture/SKILL.md:764-765` and `CLAUDE.md:21` quotes — verbatim.
- `assignee: agent` on `coga/workflows/autoclose-merged/sweep.md` with no agent involved — confirmed, and the description of that workflow as existing only to name the skill is fair.
- `755e60de` did touch contexts, templates, README, `docs/vision.md`, `docs/market-thesis.md`, `docs/concepts.md`, `docs/reference.md` — 25+ files. The "large prose surface" warning is understated if anything.

**Wrong — fix before launch:**

1. **"Two vestigial `script:` declarers survived the scrub as twins: `coga/show` and `coga/ticket/finalize`."** This is false. Both were scrubbed *in the same commit*: `755e60de` deleted `coga/skills/coga/show/run.py` and `coga/skills/coga/ticket/finalize/run.py` and rewrote both SKILL.md files. `coga/skills/coga/ticket/finalize/SKILL.md` now ends with *"The command owns this lifecycle directly; this skill documents the shared behavior and does not provide an executable entry point."* Nothing in the repo declares `script:` today. The only `script:` occurrences are inert `script: null` keys in ~20 legacy tickets, which `Ticket.parse` strips (`src/coga/ticket.py:72-78`). A design agent sent looking for surviving twins to model on will find nothing and waste the step.

2. **"`validate.py` gained coverage rejecting a leftover non-null `script:` key — that check is a direct obstacle and will need revisiting."** Backwards. There is no `script` handling in `src/coga/validate.py` at all (the only match for "script" is an argparse description string). The test is `tests/test_validate.py:339`, named `test_validate_tolerates_legacy_non_null_script_key`, and it asserts *tolerance*: `assert all(issue.severity == "warn" for issue in issues)`. A leftover `script:` degrades to an orphan-extension warning; it does not fail validation. This is not an obstacle — it is close to a free path. The real work is adding `script` to `CANONICAL_TICKET_KEYS` in `ticket.py` and removing the `fm.pop("script")` migration. Rewrite this bullet; as written it points the design at a hard gate that doesn't exist.

3. **"All four recipe-backed templates carry the same comment."** There are **five**: `autoclose-merged`, `blocker-reminders`, `branch-sweep`, `digest`, `skill-update`. All five carry the comment. Relatedly, option 2's "Removes four workflow files" is right only for `coga/workflows/` (`autoclose-merged/sweep`, `blocker-reminders/run`, `branch-sweep/sweep`, `skill-update/run`) — the fifth, `digest/post`, has **no live `coga/workflows/digest/` directory** and exists only at `src/coga/resources/templates/coga/bootstrap/workflows/digest/post.md`. That asymmetry is a real wrinkle for the trim design and for CLAUDE.md's keep-both-copies-in-sync rule; it should be in the ticket, not discovered mid-design.

4. **"`task_env.py` already builds the shared `COGA_TASK_*` contract […] so the env-passing half of this likely exists already."** Half right, and the wrong half is load-bearing. `task_env.py` gives task *identity* (`COGA_TASK_SLUG/DIR/TICKET/BLACKBOARD/LOG`, `COGA_REPO_ROOT`, …) for both paths — true. But the **argv channel died with the seam**: `apply_arg_env`, `COGA_ARG_1..N`, `COGA_ARGC` lived in `launch_script.py` and are gone. If the new shape takes arguments, that is rebuild work, not reuse. As written this bullet will make the design under-scope.

5. Nit: `recurring.py:76-95` is really `:76-87`; line 88 is the `return cls(...)`.

## Description

Clear on *why*, thin on *what a finished design looks like*. An agent can start, but has no target. Add explicit acceptance criteria for the design step — the spec must state: (a) the declaration surface (frontmatter field? step `assignee: script`? a `coga run` extension?); (b) whether it is per-ticket or per-step, and whether it can appear mid-workflow; (c) the argv/env contract (see #4 above); (d) headless vs TTY and how `coga recurring` / the REPL supervisor treat it; (e) the exact prose deltas to `CLAUDE.md`, `AGENTS.md`, `coga/extension-model`, `coga/codebase`, `coga/architecture`, `coga/recurring`; (f) whether `validate` makes `script:` canonical.

One overstatement to correct: *"the only home for deterministic Coga behavior is `runner.RECIPES` inside `src/coga/`."* `CLAUDE.md:21` already permits it — *"A single-consumer helper may live beside the ticket or skill that uses it, import only shared core infra, and be invoked explicitly by agent instructions."* Deterministic code at the edge is allowed today. The actual gap is **headless execution with no agent in the loop**. Your first paragraph says this correctly ("no LLM in the loop") and your second contradicts it. Fix the second, or the design will attack a strawman and the owner will bounce it at `review-design`.

## Workflow fit

`code/design-then-implement` is the right choice, and `review-design` is exactly the correct gate for a proposed reversal of a merged decision. Two caveats:

- **No sanctioned "don't do this" exit.** The workflow prose offers bump-forward or relaunch-design. If the design concludes #670 was right, the ticket has to be blocked or canceled by hand. Say in the Description that a design concluding *the current contract stands* is an acceptable outcome — otherwise the agent will feel obligated to manufacture a reversal, which is the failure mode this ticket is most exposed to.
- **One `implement` step, one PR, 25+ files.** `755e60de` is the size of the mirror-image change. That is a lot for a single owner review at the `review` gate. Have the design propose a split (capability + tests first, prose-contract sweep second), or accept the size explicitly.

## Contexts

`coga/extension-model` at 42% is **justified** — it is the document being rewritten, and the design needs its whole "Three homes / reach for the lowest tier" decision procedure, not just the conclusion. The two passages already quoted in `## Context` are the conclusions; the reasoning around them is what the design has to engage. Keep it attached. Do not swap it for a quote.

The problem is what's *missing*, not what's oversized. The composed prompt is 26.5 KiB / ~6.7k tokens — this ticket is under-loaded, not over-loaded. (Note the report reflects the `draft` state; once the workflow freezes, the `design` step composes `code/design` at 3.3 KiB, ~830 tokens.)

- **Add `coga/principles`** (10.8 KiB, ~2.7k tokens). It holds the non-negotiables the whole microkernel argument rests on. Total would land near ~9.5k tokens — still small. Cheapest high-value add on the list.
- **`coga/codebase`** (21.9 KiB) is what `CLAUDE.md` points to for "the full rule," and `755e60de` edited 49 lines of it. The design must change it. Attach it, or at minimum give the path explicitly under Context.
- **`coga/architecture`** (53.8 KiB) is too big to attach — correct call to quote it instead. But the ticket names "`coga/architecture`" in prose with no path. Give `coga/contexts/coga/architecture/SKILL.md:764-765` so the design can read the surrounding argument, which is the strongest counter-case it has to beat.
- **`coga/recurring`** (25.6 KiB) — same treatment; the `recipe:` half of the ticket lives there and `755e60de` edited 60 lines of it. Path, not name.

## Scope

**This is two tickets.** Ticket A: can an ordinary ticket execute as a script (capability + contract reversal). Ticket B: `recipe:` duplicates the one-step workflow on recurring templates (a trim of existing plumbing). B is decidable and shippable today, standalone, and does not need A.

The Description declares A the ticket and B "the symptom." Then `## Context` opens with thirty lines on B and hands the design two named options to choose between. That inverts the stated priority, and a design agent reading cold will produce a spec covering both — after which `implement` produces a PR that mixes a contract reversal with a recurring-template refactor. Either split B out now, or cut its two options down to one line ("this surfaced from the `recipe:`/one-step-workflow duplication; tracked separately") and drop the instruction to pick a trim.

`## Out of Scope` correctly excludes migrating the ten `RECIPES` entries. Good.

## Assumptions to question before launch

1. **The reversal is framed as binary and it isn't.** There is a third shape the ticket never names: keep `runner.RECIPES` as the explicit *dispatch* surface but let a recipe's implementation live beside its ticket via declarative registration — no plugin host, no recursive discovery, still legible and reviewable. That satisfies every stated reason for #670 *and* the microkernel goal without restoring `script:`. Tell the design to consider a middle path, or `review-design` degrades into a yes/no vote on a reversal.

2. **"Kernel grows" is measured in the wrong unit.** Ten `RECIPES` entries is ten lines in a dict. The actual code lives in `autoclose.sweep_merged`, the digest module, and so on — most of which is arguably shared infra that stays in core either way. The design must quantify what LOC *actually leaves* `src/coga/` under its proposal. Without that number the microkernel argument is rhetorical and a #670 defender will say moving ten dict entries shrinks nothing.

3. **Assumed reuse of the env plumbing** — see factual point 4. Do not let "likely exists already" stand unqualified.
