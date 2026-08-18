---
slug: recurring-recipe-question
title: Deduce whether a ticket is a script or an agent prompt
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/extension-model
- coga/principles
- coga/codebase
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
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (review-design)
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

**Row one is the point of this ticket.** A script ticket runs with no LLM
anywhere in the path: `coga launch <slug>` is plain Python that inspects the
directory, finds the entry point, and subprocesses it. No prompt is composed, no
agent session is started, no tokens are spent, nothing waits on a model. That is
the whole objective — the deterministic path must be *deterministic*, not an
agent that has been instructed to run a script.

State that as an explicit non-goal to guard against: an agent must never be the
thing that launches the script. If the implementation composes a prompt telling
a model to invoke the entry point, it has failed, however correct the result
looks.

Row three is a useful consequence, not the motivation: when a ticket does have
agent work, the deterministic part still runs as code first. The handoff needs
no new channel — **the blackboard is already a composed prompt layer**, so a
script that appends its findings is automatically feeding the agent behind it,
with the handoff visible in git. Recipes already work this way (`task_env.py`
hands them `COGA_TASK_BLACKBOARD`).

`recipe:` is then not a thing to trim — it is a thing that stops existing once
the classifier can deduce the same fact. It goes in this ticket; see *"Deleting
`recipe:` is a format change, not a migration"* under Context for why that costs
no implementation moves.

### What the design step must deliver

The `design` step writes a spec that states, at minimum:

- **The two signals, and how each is read.** "Is there a script here" is the
  easy one — settle the entry-point name, whether the executable bit counts, and
  what happens with more than one candidate or a non-executable `run.py`.

  **"Does this ticket have work for an agent" must be answered structurally.**
  By `ls`, by section shape, or by whether the current workflow step carries
  agent skills — never by reading the prose and judging its intent. Judging
  intent would mean consulting a model to decide whether to consult a model,
  which defeats the entire purpose. The current workflow step is the strongest
  candidate: a step with `skills:` and `assignee: agent` wants an agent, one
  without does not, and that is already declared, already frozen, already
  validated, and readable with no inference at all. Whatever the design picks, a
  human must be able to predict the outcome from the directory without running
  anything.

  A wrong guess here is worse than the field this replaces: silently skipping
  the agent half of row three does the deterministic work and then stops, which
  looks like success. Say what makes that loud.
- **Where the classifier lives** — one ordinary Python function, called by `coga
  launch` and by the recurring runner, so both paths deduce identically rather
  than keeping two notions of "what kind of thing is this." It runs before any
  prompt is composed and decides whether composition happens at all.
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

## Acceptance Criteria

Scoped to **PR 1** (the capability). The recurring migration and the prose
sweep are PR 2 — see *Proposed Shape → The split*.

- [ ] A directory-form task holding `ticket.py` launches with **no LLM in the
      path**: `coga launch <slug>` composes no prompt and spawns no agent
      process. Proven by a test that runs with `claude` and `codex` absent from
      `PATH`, `stdin`/`stdout` not TTYs, and asserts `compose_prompt` is never
      called.
- [ ] That launch is **not** refused by `_refuse_tty_launch`; the TTY gate and
      every other agent-only preflight (agent-type resolution, `shutil.which`,
      compose pre-flight, push-auth preflight) run only when an agent is
      actually going to be spawned.
- [ ] The entry point receives, verifiably: `cwd = host_repo_root(cfg)`;
      `COGA_TASK_SLUG`, `COGA_TASK_DIR`, `COGA_TASK_TICKET`,
      `COGA_TASK_BLACKBOARD`, `COGA_TASK_LOG`, `COGA_TASK_STEP`,
      `COGA_COGA_OS_ROOT`, `COGA_REPO_ROOT`; and every value declared in the
      ticket's `secrets:`. The script is run with **no operands**
      (`sys.argv[1:] == []`) — the argument channel is out of scope.
- [ ] Non-zero exit **halts**: no agent is spawned, the ticket is left at its
      current step in `in_progress`, the exit code is propagated by `coga
      launch`, one `💥 script failed` notification is posted (`fatal=False`),
      and `coga/log.md` records the exit code.
- [ ] Exit 0 **without completing the step**, on an agent-assigned step with an
      agent available: the agent session for the **same step** is composed and
      spawned, and the composed prompt contains what the script appended to the
      blackboard (the row-three handoff needs no new channel).
- [ ] Exit 0 without completing the step, with **no agent available** (no TTY,
      no CLI, or a human-assigned step): `coga launch` exits non-zero naming the
      slug and step, the ticket stays `in_progress`, and nothing is marked done.
      The deterministic half's work is kept, not rolled back.
- [ ] Exit 0 **having completed the step** (the script ran `coga bump` /
      `coga mark done` / `coga block`): no agent is spawned for that step, the
      workflow advanced exactly once, and the launcher performed **no**
      auto-advance of its own.
- [ ] A `ticket.py` beside a bootstrap command ticket runs with no lifecycle
      writes and no `COGA_TASK_BLACKBOARD`; the launcher's own progress notes go
      to stderr so `$(coga <verb>)` captures only the command's stdout.
- [ ] `coga validate` reports a new `unrunnable-script-entry-point` finding for
      a `ticket.py` that fails `compile()`, and `coga validate --task <slug>` is
      clean for a good one.
- [ ] `COGA_TASK_STEP` is added to `coga.task_env.TASK_ENV_KEYS`, so
      `tests/conftest.py::_clear_supervised_session_env` scrubs it without a
      second edit.
- [ ] **No new frontmatter field.** `CANONICAL_TICKET_KEYS` is unchanged, no
      `script:` / `recipe:` / `assignee: script` is introduced, and the ~20
      legacy inert `script: null` keys are left inert.
- [ ] The contract prose that this makes false is corrected **in this PR**:
      `CLAUDE.md`, `AGENTS.md`, and the `coga/extension-model`, `coga/codebase`,
      `coga/architecture` contexts plus their packaged twins under
      `src/coga/resources/templates/coga/bootstrap/contexts/`. Each states the
      classifier, states explicitly that core **subprocesses** an entry
      point and still never **imports** from a ticket or skill directory, and
      states that only the reserved `ticket.py` name triggers script mode —
      any other attachment, including scripts the agent invokes, is untouched.
- [ ] `python -m pytest` green; `coga validate --json` clean.

## Proposed Shape

### The rule, in one sentence

> **Run the ticket's deterministic half if it exists; then, if the step is
> still open, run its agent half.**

The owner's table asks two questions. The first — *is there a script here* — is
answered by one `stat()`. The second — *does this ticket have work for an
agent* — is answered not by a second static signal but by the completion
contract Coga already runs on: **a step is not done until something completes
it.** Agents live under that rule already ("run `bump` as the *last* thing in
the current step"). Applying the same rule to the deterministic operator makes
all three rows fall out of one mechanism:

| directory | script's own ending | what runs |
| --- | --- | --- |
| `ticket.md` only | — | agent alone |
| `ticket.md` + `ticket.py` | script completes the step (`coga bump` / `mark done` / `block`) | **script alone** — no prompt, no agent, no tokens |
| `ticket.md` + `ticket.py` | script exits 0, step still open | **script, then agent on the same step** |

Why this rather than a second static signal (the ticket floats "the current
workflow step carries agent skills"): **it makes the dangerous direction
impossible.** The ticket names the failure that would be worse than the field it
replaces — silently skipping the agent half of row three, which looks like
success. Under a static signal that failure is an *omission* (a step that
happens to declare no skills), and omissions are exactly what nobody notices.
Here, skipping the agent half requires the script to take the affirmative,
git-visible, Slack-broadcast action of declaring the step finished. Forgetting
to do so fails *toward* running the agent — visible, costs tokens, skips
nothing. Every guess this design can get wrong is a guess in the safe direction.

It is also structural in the sense the ticket demands: nothing reads prose and
judges intent. The launcher reads `status` and `step` out of frontmatter after
the script exits — the same two fields `_harness_stop_reason` already reads
after an agent exits. And a human predicts the outcome from the directory: `ls`
shows whether there is a deterministic half, and the last lines of `ticket.py`
show whether it closes the step. Both are in the directory, both are code, not
prose.

**Fallback if the owner rejects that.** Keep the static form: `agent_work =
current step declares at least one `skills:` entry AND its frozen `assignee`
role resolves to a configured agent`. Everything else below is unchanged except
that (a) PR 2 must rewrite the five recurring one-step workflows to `skills: []`
plus an inline instruction section, since as written every one of them declares
a skill and would classify as row three, and (b) the loudness requirement moves
onto `coga validate`, which would have to warn when a directory holds
`ticket.py` and a skill-bearing step — a weaker guarantee. See *Open Questions*.

### The entry point

**`ticket.py`, in the task directory, exactly that name.**

- One fixed name means one `stat()` — not a scan, not a glob, not a precedence
  rule, so "more than one candidate" cannot arise.
- `ticket.md` / `ticket.py` reads as the two halves of one ticket. That is why
  not `run.py`: a task directory is also where attachments live, and "here is
  the repro script, `run.py`" is a genuinely likely attachment on a bug ticket.
  Nobody attaches a file called `ticket.py` by accident.
- **The executable bit is not consulted.** It is invisible to `ls` and to a
  reader browsing GitHub, and it is lost by zips and some checkouts. The name is
  the signal; the file is always run as `[sys.executable, str(path)]`, so
  it imports the same installed `coga` the launcher is running.
- **A script the *agent* calls is a different, untouched mode** — the
  `CLAUDE.md` edge helper "invoked explicitly by agent instructions." It needs
  no classifier and no special name, and an attachment meant for the agent must
  **not** be named `ticket.py`, or it becomes the ticket's deterministic half.
  The contract prose states this rule explicitly rather than leaving it
  implied.
- File-form tasks (`tasks/<slug>.md`) can never be script tickets — they have no
  directory. No error is needed; the `stat()` simply cannot match.
- Only `.py`. A shell-native job wraps three lines of `subprocess.run`. The cost
  is small and buys a single unambiguous name and a single execution rule.

### Where it lives

New module **`src/coga/launch_script.py`** (the name `755e60de` freed), holding
the whole deterministic path so `commands/launch.py` keeps only a call site:

- `script_entry_point(ref: TargetRef) -> Path | None` — the classifier. One
  `stat()` on `(ref.task_dir or ref.path.parent) / "ticket.py"`. Pure, no config,
  no IO beyond the stat; trivially unit-testable and callable from `validate`.
- `run_script_phase(cfg, ref, ticket, *, stateless) -> ScriptPhaseResult`
  — preflight secrets, flip `active → in_progress`, append + `git.sync_log` the
  launch line, subprocess the entry point, log the exit code, and on non-zero
  post the failure notification. Restored in substance from the deleted
  `launch_script.py`, minus `_advance_after_script`, minus skill scripts, minus
  inline `## Script` blocks, minus `apply_arg_env`.
- `ScriptPhaseResult` — `exit_code`, and the re-read `Ticket` (a fresh read is
  mandatory: the script has very likely appended to the blackboard region of the
  same `ticket.md`, and any `Ticket` held from before the run would clobber it).

`commands/launch.py` changes in three places, all inside the existing
supervisor loop:

1. Compute `entry = script_entry_point(ref)` once, right after target
   resolution. When it is non-`None`, **defer** the agent-only preflights (TTY
   refusal, `cfg.agent_type`, `shutil.which`, the compose pre-flight, and
   `_preflight_push_auth`) out of the pre-loop block and into a helper the loop
   calls only when it is about to spawn. That deferral is the bulk of the
   diff and is what makes row one LLM-free rather than LLM-free-looking.
2. At the top of each iteration of the `while True:` loop, if `entry` exists,
   call `run_script_phase`. Non-zero → `sys.exit(code)`. Zero → re-read and ask
   `_harness_stop_reason(ref, before, after, cfg)` — the *existing* function,
   unchanged — whether the step is still open. It already returns a reason
   string for terminal / paused / advanced / handed-off and `None` for "still
   the agent's turn", which is exactly the question being asked.
3. Only when that returns `None` do the deferred preflights run and the agent
   spawn happen, for the same step.

Consequence worth stating: the entry point is invoked **once per step**, not
once per launch, and receives `COGA_TASK_STEP`. A one-step ticket (every
recurring job) never notices. A multi-step ticket whose deterministic half
belongs to one step gates on that variable in its first three lines. That is
deliberately dumber than reviving per-step skill scripts.

### Argv and env

- **No script arguments in v1** (owner call, 2026-08-18). The entry point is
  always run as `[sys.executable, str(path)]` — no operands. The recurring jobs
  need none, and deferring the channel keeps PR 1 smaller. Trailing launch
  arguments keep their existing meaning untouched: they reach the *agent* half
  through the `## Launch arguments` prompt block, exactly as today. If a script
  ticket ever needs parameters, that is a later ticket — and it will pass real
  argv, never a revived `COGA_ARG_1..N` / `COGA_ARGC` env channel
  (`coga/principles` §3, reuse the OS).
- **Env** is `build_launch_env(cfg, ticket.secrets)` (same secret chokepoint as
  an agent launch — a missing declared secret is a launch refusal, not a started
  task) then `apply_task_env(env, cfg, ref)`. One new member,
  **`COGA_TASK_STEP`** (`"<n> (<name>)"`, absent for a bootstrap ticket or a
  workflow-less ticket), added to both `build_task_env` and `TASK_ENV_KEYS`.
- The script does **not** receive the supervised witnesses (`COGA_SUPERVISED`,
  `COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`) — those mint one composed *agent*
  step. A nested outer supervisor is still released correctly, because the
  script's own `coga bump` / `mark` / `block` emits the slug-scoped done marker;
  the launcher emits nothing on the script's behalf.

### Execution model and TTY

Headless is the default and the point. A script phase never touches
`repl_supervisor`, never allocates a PTY, and never checks for a TTY.

- `coga launch <script-ticket>` works from cron, a pipe, or a sandbox.
- `coga recurring` (PR 2) stops having its own dispatch entirely: it calls
  `launch` for every template, and the classifier decides. That is what makes
  "both paths deduce identically" true by construction rather than by
  maintenance. `scan_due` / `create_template` replace their `template.recipe`
  TTY pre-filter with `script_entry_point(...) is not None`.
- `coga megalaunch` needs no change: it requires a TTY for the run as a whole
  (its REPLs are interactive transport), and a script-backed ticket in the queue
  simply finishes without using it.
- **Row three with no TTY refuses the agent half loudly** — non-zero exit naming
  the slug and step, ticket left `in_progress`, deterministic work retained.
  It does not "run the script and skip the agent with a warning": that is the
  looks-like-success shape this design exists to eliminate.

### Failure and lifecycle

- **Non-zero script exit halts the launch.** No compose, no spawn. The ticket
  stays at its step; the exit code, a log line, and one Slack post carry the
  failure. Identical to today's `_run_recipe_task` behavior for a failed recipe.
- **The launcher never advances the workflow on the script's behalf.** This is
  the one deliberate regression against the deleted `launch_script.py`, which
  auto-bumped on exit 0 (`_advance_after_script`), and against
  `_run_recipe_task`, which auto-`mark_done`s. Auto-advance is precisely the
  mechanism that would silently swallow row three. The script completes its own
  step, exactly as an agent does.
- `bump`, `block`, and blackboard writes need nothing new: they are ordinary
  CLI commands and an ordinary file the script already has a path to.

### The recurring shims (PR 2), concretely

A period task is built from the template's frontmatter and body — siblings are
not copied — so `_create_at_slug` gains one line: copy `ticket.py` from the
template directory into the created period task directory, alongside the body it
already carries verbatim. (Only `ticket.py`; `digest/spool.md` stays with the
template by design.) Each of the five templates gets its own eight-line shim —
no shared dispatcher, because a shared one is `runner.RECIPES` again with extra
steps:

```python
#!/usr/bin/env python3
"""Deterministic half of the autoclose-merged period task."""
import os, subprocess, sys

from coga.autoclose import run_autoclose_recipe
from coga.config import load_config

code = run_autoclose_recipe(load_config(), [])
if code:
    sys.exit(code)
sys.exit(subprocess.run(
    [sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]]
).returncode)
```

Note the shim completes the step through the **CLI**, not by importing
`commands.bump` — calling a Typer command function in-process passes
`OptionInfo` sentinels (`coga/codebase`, "Gotchas"). It imports only shared core
infra (`coga.autoclose`, `coga.config`), which is exactly the edge shape
`CLAUDE.md` already sanctions, and **core still never imports the shim** — the
dependency arrow is unchanged, and the classifier subprocesses a path rather
than importing a module.

Packaging note: the templates that ship in the wheel gain a `.py` file, which
flips their directories from "pure data" to "contains Python" — the exact shape
behind the documented package-walk vs `force-include` wheel trap
(`coga/codebase`, "Wheel packaging"). The bootstrap tree's existing
exclude+force-include pairing should already cover it, but PR 2 must verify the
wheel builds on a **pristine** clone, not just a dev tree. The name itself
costs nothing on the Python side: shims are subprocessed by path, never
imported, and `coga/` in a working repo is not a package, so a task-directory
`ticket.py` cannot collide with core's `src/coga/ticket.py`.

`runner.RECIPES` and `coga run` **survive this work unchanged.** Their role
narrows rather than ends: they stop being the only door out of core and remain a
public headless command surface that agents, humans, and now shims invoke by
name (`coga run open-pr`, Dream's `coga run validate-drift`). Trimming the table
is a later per-job judgment, not part of either PR.

### Where unit tests live

- **Coga's own scripts** — the five shims and any future bundled script
  ticket — are covered from `tests/` like everything else: subprocess the entry
  point against the seeded `example/` fixture. Never by collecting the live
  dogfooded `coga/` tree ("tests must not pin to live dogfooded state",
  `coga/codebase`).
- **Scripts in user repos** are the repo's own business. Tests may sit beside
  the ticket (any name but `ticket.py`), but Coga neither collects nor runs
  them — the launcher has no test-discovery machinery. The sanctioned shape
  keeps `ticket.py` thin; the imported logic is what carries the real tests.

### Answering #670

#670 deleted this capability for four stated reasons. Three survive intact and
one is met head-on:

- **"No recursive discovery."** This is the crux and cannot be routed around, so:
  a classifier that reads file presence *is* a file changing behavior. What it
  is not is discovery in #670's sense — scanning a tree to find capabilities the
  system will then offer somewhere. This is one `stat()` at one fixed path
  inside the target's own directory, affecting that target and nothing else,
  with no registry to consult and nothing enabled anywhere. Dream's contract
  ("dropping a SKILL.md under `bootstrap/dream/tasks/` does not enable it")
  stays literally true: it is about a *scan*, and there is still no scan. The
  distinction that must hold for this design to be legitimate is *scan vs.
  stat, system-wide vs. self* — if the owner judges it does not hold, the
  honest outcome is the fallback middle path, not a softer word for scanning.
- **"No plugin host."** Preserved and strengthened: core subprocesses a path. It
  imports nothing from the edge, offers no API, defines no hooks, no load order,
  no extension points. Skills remain process contracts — skill `script:`
  frontmatter is **not** coming back, and neither are inline `## Script` fenced
  blocks or a `script:` ticket field. This restores strictly less than #670
  deleted: one fixed filename, task directories only.
- **"Legibility."** This argument cuts *toward* the change for the recurring
  templates. `ls coga/recurring/autoclose-merged/` showing `ticket.md` +
  `ticket.py` is more legible than `recipe: autoclose` pointing into a Python
  table the reader must go find — and it deletes the triple declaration
  (`recipe:` + a one-step workflow that exists only to name a skill +
  `assignee: agent`, which is false).
- **"Reviewability."** Unchanged: `ticket.py` is a git-tracked file reviewed in
  the PR that adds it. What changes is *who* reviews it and how far a mistake
  reaches — a ticket's owner, in one ticket directory, instead of a core change
  everyone inherits. One honest caveat to record rather than hide: in a repo
  where `coga/tasks/**` is reviewed more loosely than `src/coga/**`, this widens
  what a task-directory diff can do. Coga's own trust model already treats both
  as "anyone who can write this repo", so the threat model does not move here —
  but a team that splits those permissions should know it.

### The microkernel claim, stated honestly

No implementation leaves `src/coga/` in either PR, so nothing shrinks. The
narrow, checkable claim is: **a new deterministic feature can now ship entirely
at the edge.**

Smallest end-to-end demonstration — a nightly "PRs open longer than 7 days"
Slack reminder. Today: a new module in `src/coga/`, a new name in
`runner.RECIPES`, tests in `tests/`, a skill, a one-step workflow, and
`recipe: stale-prs` on the template — five surfaces, three of them core. After:
`coga/recurring/stale-prs/ticket.md` (schedule + body) and
`coga/recurring/stale-prs/ticket.py` (shells `gh pr list`, posts via `coga
slack`, ends with `coga bump`). Two files, one directory, **zero** core edits and
zero core tests. That is the whole claim, and it is verifiable by writing it.

### The split

The reach is exactly what the ticket predicted, so split at the seam between
*capability* and *migration + prose*:

- **PR 1 — this ticket.** `launch_script.py`, the `commands/launch.py`
  restructure, `COGA_TASK_STEP`, the `validate` check, tests, and only the
  contract prose that PR 1 makes actively false (`CLAUDE.md`, `AGENTS.md`,
  `coga/extension-model`, `coga/codebase`, `coga/architecture` + packaged
  twins). `recipe:` keeps working untouched: a template with `recipe:` and no
  `ticket.py` takes the existing path, so the intermediate state is coherent and
  shippable on its own.
- **PR 2 — a sibling ticket.** The five shims, the `_create_at_slug` copy, the
  deletion of `recipe:` (`Template.load`, `Template.recipe`, `DueTask.recipe`,
  `_run_recipe_task`, both TTY pre-filters), reshaping the five one-step
  workflows and their skills, the `digest/post` live↔packaged sync, and the full
  prose sweep — `coga/recurring`, `coga/cli`, `coga/sync`, `coga/patterns`,
  `coga/roadmap`, `marketing/positioning`, `README.md`, `docs/vision.md`,
  `docs/concepts.md`, `docs/reference.md`, `docs/market-thesis.md`,
  `docs/cli-extension-audit.md`.

Putting 25+ prose files and a live recurring migration behind the same owner
review as the mechanism is what the ticket asked to avoid.

## Out of Scope

- **Migrating the ten `runner.RECIPES` implementations out of `src/coga/`.** The
  format change decouples this completely; each is its own later judgment about
  whether that code is still shared infra.
- **Rewriting the implementations themselves.** Behavior changes to `autoclose`,
  `digest`, and friends belong in their own tickets.
- **Trimming `runner.RECIPES` or `coga run`.** Both survive as a public headless
  command surface.
- **Reviving skill `script:` frontmatter, inline `## Script` blocks, or a
  `script:` / `recipe:` ticket field.** All three stay deleted; this design
  restores strictly less than `755e60de` removed.
- **Any script argument channel.** v1 entry points take no operands; the
  recurring jobs need none. If a script ticket ever needs parameters, that is a
  later ticket — and it will pass real argv, never a revived `COGA_ARG_1..N` /
  `COGA_ARGC` env channel.
- **Scrubbing the ~20 legacy inert `script: null` keys.** `Ticket.parse` already
  strips them on rewrite; a sweep buys nothing.
- **The recurring migration and the 25-file prose sweep** — PR 2, per the split
  above.

<!-- coga:blackboard -->

## Design step — findings

Verified against the tree, not inferred:

- `git show 755e60de^:src/coga/commands/launch_script.py` is the full prior art
  (492 lines). PR 1 restores roughly `run_script_mode`'s spine and deliberately
  drops `_advance_after_script`, `_resolve_skill_script`, `_resolve_inline_script`,
  and `apply_arg_env`.
- The old seam was *already* half-deduced: `current_step_is_script` read the step
  skill's `script:` frontmatter. So "deduce, don't declare" is not new ground —
  only the signal changes.
- **Period tasks do not inherit template siblings.** `_create_at_slug`
  (`recurring.py:819`) passes only frontmatter + `body=template.body` to
  `create_task`. A shim beside a template is invisible to a classifier reading
  the *task* directory, so PR 2 must copy `ticket.py` across. Missing this would
  produce two notions of "what kind of thing is this" — the exact failure the
  ticket forbids.
- All five recipe one-step workflows declare `skills: [...]` + `assignee: agent`
  (`autoclose-merged/sweep`, `blocker-reminders/run`, `branch-sweep/sweep`,
  `digest/post`, `skill-update/run`), and so does `direct/body`. Under a static
  "step carries skills" signal every one of them classifies as row three; they
  would all need rewriting. This is the main practical argument for the
  completion-contract rule.
- `_harness_stop_reason` (`launch.py:2258`) already answers "is this step still
  the agent's turn" from `status` + `step` alone. The design reuses it verbatim
  rather than adding a second notion of step completion.
- `COGA_TASK_STEP` is free — the supervisor uses `COGA_EXPECTED_STEP`.
- `validate.py` has no `script` handling; the only related coverage is
  `test_validate.py:339` asserting *tolerance* of a legacy `script:` key.

## Open Questions

1. **Is the completion-contract answer to "does this ticket have work for an
   agent" acceptable?** The spec deduces it from whether the script completed
   the step, rather than from a second static signal read before running
   anything. It is structural (frontmatter `status`/`step`, never prose) and its
   only wrong guess is the safe one, but it means a human predicts row one vs.
   row three by reading `ticket.py`'s last lines rather than by `ls` alone. The
   fallback — `skills:` + agent `assignee` on the current step — is specified in
   Proposed Shape and costs a rewrite of all six one-step workflows plus a
   weaker loudness guarantee. **This is the one decision that changes the shape
   of the work.**
2. **`ticket.py` as the name.** Chosen over the historical `run.py` because a
   task directory also holds attachments and "here's the repro script, `run.py`"
   is a plausible accidental trigger. Trade-off: it sits next to core's own
   `src/coga/ticket.py` in conversation, if not on disk. — **Resolved
   2026-08-18: owner keeps `ticket.py`** (see Owner feedback below).
3. **Does the split land as specified?** The ticket says `recipe:` deletion
   "goes in this ticket"; the spec moves it to PR 2 with the prose it describes,
   leaving PR 1 shippable on its own. If the owner wants one PR, PR 1's
   acceptance criteria absorb PR 2's list unchanged.
4. **Scan vs. stat.** If the owner judges that one `stat()` inside a ticket's own
   directory is still the discovery #670 closed the door on, the honest outcome
   is the declarative-registration middle path (implementations beside their
   tickets, `runner.RECIPES` kept as the explicit dispatch surface) — which
   keeps a declaration and so only partly meets the no-new-field constraint. Say
   so at `review-design` and the spec becomes that instead; it is not worth
   building the classifier first to find out.

## Owner feedback — review-design (2026-08-18)

Partial review; open questions 1, 3, and 4 still await the owner's call.

- **Keep `ticket.py` as the name** (open question 2 resolved). The packaging
  worry was checked and does not bite: shims are subprocessed by path, never
  imported, and `coga/` in a working repo is not a package. The one real trap —
  the wheel package-walk vs `force-include` collision when packaged template
  dirs gain a `.py` — is now called out in the spec with a pristine-clone
  build check in PR 2.
- **Defer script arguments.** v1 entry points take no operands; the argv
  passthrough was cut from PR 1's acceptance criteria and moved to Out of
  Scope. Trailing launch args keep their existing agent-side meaning.
- **Agent-called attachment scripts stay a separate, untouched mode** and must
  not be named `ticket.py` — now an explicit rule in "The entry point" and to
  be stated in the contract-prose deltas.
- **Test placement added to the spec**: Coga's own scripts are tested from
  `tests/` via subprocess against the `example/` fixture; user-repo script
  tests live beside the ticket but Coga never collects or runs them.
