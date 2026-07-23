---
slug: remove-run-py-everywhere
title: remove run.py everywhere
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
script: null
---

## Description

Remove Coga's launch-integrated script-seam entirely and replace it with a
single generic runner. Today a skill or ticket declares `script: run.py` (or a
sibling/inline script), and `coga launch` detects that via `is_script_launch`
and runs it with no agent through `launch_script.py`. That seam is spread across
the ticket model and shows up as ~6 live + ~12 packaged `run.py` wrapper files.
Most are only a thin entrypoint over a recipe that already lives in a `coga.*`
core module — but `open-pr` is a genuine exception (see Context): it carries
real seam logic and its recipe lives in a sibling `recipe.py`, not an importable
module, so it must be ported, not deleted.

The goal is to delete the seam — no `script:` frontmatter field, no
`is_script_launch` branching in `launch`, no `launch_script.py`, no
`COGA_ARG_*` env plumbing, no per-skill `run.py` — and replace it with one
generic `coga run <recipe>` command backed by a name→function dispatch table
over the existing recipe modules. Deterministic recurring jobs and the PR path
invoke that runner directly instead of being launched as a script step.

Why: the seam is confusing and duplicative. The real logic already lives in
`coga.*` modules; the `run.py` files, the `script:` field, and the 520-line
`launch_script.py` are wrapper machinery threaded through `launch`, `recurring`,
`megalaunch`, `validate`, `views`, and more. Collapsing it to one runner removes
a whole concept from the ticket model and stops `run.py` from proliferating.

Done looks like: no `run.py` files remain (live or packaged), the `script:`
concept is gone from the ticket model and validation, every deterministic job
that used to be script-launched now runs via the generic runner, and the test
suite plus `coga validate` pass.

## Context

**This is a large, cross-cutting refactor — hence the design-first workflow.**
The `design` step should produce a concrete spec (new runner shape, dispatch
table location, per-consumer migration, deletion order) for the owner to review
before any code is written.

Current seam, for grounding:

- `script: run.py` skills run without an agent. Example:
  `coga/skills/coga/blockers/remind/run.py` is ~20 lines that import
  `coga.blocker_reminders.remind_blocked_tasks` and call it. All the real logic
  is already in the core module; the wrapper is the only thing being removed.
- Live wrappers: `coga/skills/coga/{show,branch-sweep/sweep,autoclose/sweep,
  blockers/remind,digest/flush,ticket/finalize}/run.py`. Packaged copies live
  under `src/coga/resources/templates/coga/bootstrap/...` (open-pr,
  recurring-scan, skill-update, delete-task, dream/{cleanup-orphan-markers,
  validate-drift}, plus the mirror of the live ones). Live and packaged copies
  must stay in sync.
- Dispatch entrypoint: `src/coga/commands/launch_script.py` (~520 lines) exposes
  `is_script_launch`, `current_step_is_script`, `run_script_mode`.
- The `script:` field is consumed across `launch.py`, `create.py`,
  `megalaunch.py`, `recurring.py`, `recurring_runner.py`, `skill.py`,
  `tasks.py`, `ticket.py`, `validate.py`, `views.py`, `delete_task.py`,
  `aliases.py`. Removing the field from the model must not break existing
  tickets that still carry an explicit `script: null` in frontmatter (including
  this one) — the migration should tolerate/strip a leftover `script:` key
  without a validation error.
- Tests to update: `tests/test_launch_script.py`, `test_launch.py`,
  `test_launch_auto.py`, `test_commands.py`, `test_recurring.py`,
  `test_autoclose_sweep.py`, `test_open_pr_command.py`.

Three distinct consumers of the seam, each needs a replacement path:

1. **Deterministic recurring jobs** — `autoclose/sweep`, `digest/flush`,
   `blockers/remind`, `branch-sweep`, `dream/{validate-drift,
   cleanup-orphan-markers}`, `recurring-scan`, `skill-update`. The recurring
   runner currently launches these as script steps; it must instead invoke the
   generic runner by recipe name.
2. **Command tickets invoked as a verb** — `coga open-pr <slug>` rewrites to
   `launch bootstrap/open-pr` and runs `open-pr/run.py` as a stateless script,
   emitting a bare PR URL on stdout. The verb + its stdout contract must survive
   on the new runner (e.g. `coga run open-pr <slug>`), including
   `COGA_ARG_*`-style argument passing being replaced by the runner's own arg
   channel.
3. **The `open-pr` workflow step** — `code/open-pr` is the `requires: pr` step
   in `code/with-review` and `code/design-then-implement`. Note it is *not*
   itself a `script:` step: its SKILL.md has no `script:` field — it is an agent
   step whose body instructs the agent to run the `coga open-pr` verb (which is
   the stateless script launch in consumer 2). So removing the seam breaks the
   underlying verb, not the step's classification; the step migrates by changing
   which verb the agent runs (e.g. `coga run open-pr <slug>`), which is smaller
   than rewiring a launch class.

Note on consumer 2's difficulty: `bootstrap/open-pr/run.py` is ~180 lines and
holds real logic that is *not* in a `coga.*` module — `_checkout_mode`
(single- vs two-checkout ownership gate), the `COGA_EXPECTED_TASK` ownership
proof, `_target_task_arg` — and its actual recipe lives in a sibling
`recipe.py`. So "a dispatch table over existing recipe modules" does not cleanly
cover open-pr: the recipe must first be promoted into an importable module, and
the design spec must preserve the `COGA_EXPECTED_TASK` ownership proofing and
the bare-PR-URL-on-stdout contract (the `requires: pr` bump gate depends on it).

**Self-hosting caveat / deletion order.** This very ticket ships on
`code/design-then-implement`, whose own `open-pr` step runs the `coga open-pr`
verb — the exact verb this ticket rewires. The implementer must land the
replacement PR-opening path before/atomically-with removing the old seam, or the
final `open-pr` step will break and the owner opens that PR by hand. Call this
out in the design spec. (The cleanest structural fix is to not carry
seam-deletion and the open-pr port in the same ticket — see the scope split in
the blackboard evaluator review.)

**Docs to update in the same PR** (behavioral contract per CLAUDE.md): the
`run.py` seam is documented in `coga/contexts/coga/architecture/SKILL.md` (the
`ticket.md` + `run.py` seam section, around line 594) and referenced in
`coga/contexts/coga/sync/SKILL.md`; each has a packaged twin under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/...` — update both
live and packaged copies.

**Out of scope / not a code change:** the ~40 `run.py` mentions in old/done
`coga/tasks/*.md` prose are historical narrative in finished tickets — leave
them; editing done tickets' text changes no behavior.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Independent cold read of the draft, cross-checked against the codebase.

### 1. Description clarity
Mostly yes — unusually well-grounded for a refactor ticket. States goal, why,
and a concrete "done looks like." Context enumerates actual files, three
consumer classes, and the deletion-order hazard. Gap: it precisely says *what
to remove* but leaves the *shape of the replacement* to the design step, and it
doesn't flag that one consumer (open-pr) is far harder than the "thin wrapper"
framing implies.

### 2. Workflow fit (code/design-then-implement)
Good fit — large cross-cutting refactor with a real design surface, so a
reviewable spec first is right. Tension: this workflow's own final step
(open-pr) is implemented by the very seam being deleted. Ticket half-acknowledges
this as a "self-hosting caveat," but the mitigation is a workaround, not a fix.
Cleaner: don't carry seam-deletion and open-pr migration in the same ticket.

### 3. Contexts (empty) vs body pointer
Pointing rather than attaching is right — architecture SKILL.md is 688 lines and
would dominate the ~3.7k-token prompt. Caveat: the body paths were wrong
(`coga/architecture/SKILL.md` → real path `coga/contexts/coga/architecture/SKILL.md`;
same for sync). [FIXED in body.] Each also has a packaged twin.

### 4. Scope — this is 2–3 tickets bundled as one
18 run.py files, 12 consumer modules, validation, two docs (×2 packaging), 8
test files. What makes it too big is that the three consumers have wildly
different difficulty, and lumping them forces the self-hosting hazard. Suggested
split:
- **Ticket A** — build `coga run <recipe>` + dispatch table; migrate the
  genuinely-thin recurring jobs (autoclose/sweep, digest/flush, blockers/remind,
  branch-sweep, dream/{validate-drift,cleanup-orphan-markers}, recurring-scan,
  skill-update). Leave old seam alive. Low risk.
- **Ticket B** — migrate open-pr: the verb, bare-URL stdout contract,
  COGA_ARG_*→runner-arg change, checkout-ownership gate, and the code/open-pr
  step. The hard one, entangled with self-hosting.
- **Ticket C** — delete the seam (script: from model, launch_script.py,
  is_script_launch/run_script_mode/current_step_is_script, validation, docs).
  Runs only after A and B leave zero consumers — which dissolves the
  self-hosting problem.

### 5. Technical claims vs actual code
File inventory accurate (6 live + 12 packaged run.py verified; launch_script.py
is 520 lines with the three named symbols; 12-module consumer list confirmed;
arch seam ~line 594; sync references it; ~40 done-ticket mentions correctly
out-of-scope). Two claims were misleading, both now corrected in the body:
- "real logic already lives in coga.* modules; run.py are thin" — TRUE for
  recurring jobs, FALSE for open-pr. `bootstrap/open-pr/run.py` is ~180 lines
  with real seam logic (_checkout_mode, COGA_EXPECTED_TASK, _target_task_arg)
  and its recipe lives in a sibling `recipe.py`, not a coga.* module. Must be
  ported, not deleted.
- "code/open-pr is a script step" — INACCURATE. Its SKILL.md has no `script:`
  field; it's an agent step whose body runs the `coga open-pr` verb. Self-hosting
  logic still holds (removing the seam breaks the underlying verb), but the step
  migration is smaller than "move a script step."

### 6. Assumptions to question
- "One generic runner cleanly replaces the seam" — open-pr isn't a plain recipe
  call; preserve COGA_EXPECTED_TASK ownership proof + bare-URL stdout or the
  `requires: pr` gate silently regresses.
- Recipe logic location — dispatch assumes importable functions; open-pr's
  recipe is a packaged sibling file; decide whether recipes get promoted into
  coga.* modules (packaged-template change needing live/packaged sync).
- Deletion atomicity as stated is a foot-gun on this workflow — prefer A/B/C.
- This ticket's own `script: null` frontmatter — confirm the model migration
  tolerates existing tickets carrying an explicit `script: null`. [Noted in body.]

**Bottom line:** strong, well-researched ticket let down by two things — it's
really 2–3 tickets whose bundling manufactures a self-hosting hazard, and it
flattened the one genuinely hard consumer (open-pr) into the same thin-wrapper
story as the trivial ones. Factual fixes applied; the scope split is the open
decision for the human.
