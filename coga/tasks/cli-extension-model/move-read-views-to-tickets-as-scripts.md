---
slug: cli-extension-model/move-read-views-to-tickets-as-scripts
title: Move show/status into their lowest-tier mechanism
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/extension-model
- coga/architecture
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
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 2 (review-design)
---

## Description

Per Nico's plan — push each command to the **lowest tier** it can use — move
zach's remaining core read commands out of `commands/*.py`:

- **`show`, `status`** (read-only views) → **tickets-as-scripts** (`mode:
  script`), per Nico's reads decision below. *(The other reads — `validate`,
  `skill status`, `recurring list` — share this destination but aren't the
  immediate focus.)*
- **`chat`, `build`** → already aliases — lowest tier already; verification
  tracked by `audit-chat-and-build-are-core-free`.
- *(`ticket`'s move is tracked separately by `move-ticket-authoring-out-of-core`
  — the redo of closed PR #425 — not part of this.)*

This is **group 1** of `cli-extension-model/move-command-logic-to-tickets`.
Immediate work: `show` and `status`. Per the *no-inversion* guardrail the
render Python relocates **unchanged**; only its home changes. Start with `show`
(a pure render of one task's files) as the proof.

**Depends on `remove-the-shim-concept` landing first** — that ticket purifies
the model (these reads are *tickets-as-scripts*, not "script shims") and
rewrites the `extension-model` contract, which resolves the contradiction noted
below.

## Decision (Nico, 2026-06-23)

Reads **do** move to tickets-as-scripts (`mode: script`) — Nico chose
"minimize core" over `extension-model`'s "reads stay commands" rule.
Consequences:
1. `extension-model` currently **contradicts** this — it says reads are
   commands and "wrapping these in a task buys nothing." `remove-the-shim-concept`
   is rewriting that contract; coordinate so the ratified context matches (flag
   to Nico at design review).
2. The **crux below still stands** — Nico set the *direction*, not the
   *mechanism*: a `mode: script` ticket can't take a transient `<slug>` arg.
3. `relay show` likely **stays** as a thin command entry that *launches* the
   script render — the command isn't removed (per zach), the render moves.

## Context

Understand these before touching code, in order:

1. `relay/extension-model` — the three homes and the two guardrails: *no
   inversion* (relocate tested Python unchanged; never rewrite a deterministic
   render as agent judgment) and *no worse Typer*. The reads are classified
   movable there.
2. The two shipped precedents to copy: `automerge → autoclose-merged/sweep` and
   `digest → digest/post` — deterministic command logic *already* running as
   `mode: script` steps. The move is "do what these did."
3. `bootstrap/orient` — the stateless ticket shape (no status/log/lock) the
   reads become.
4. The current read commands in `src/relay/commands/` (`show.py`, `status.py`,
   …) — the Python to relocate unchanged.
5. `relay/architecture` — `mode: script` launches and the env vars a script
   step receives (`RELAY_TASK_SLUG`, `RELAY_RELAY_OS_ROOT`, …).

**The crux to settle before writing code (this is the `design` step):** the
reads are *parameterized* (`relay show <slug>`, `relay status [dir]`), but a
stateless script ticket is arg-less. The central question to answer first is
*how a parameterized read hands its argument to a script step* — does it stay a
thin command that shells to a script, or something else? This is the **same
parameterized-command-to-ticket problem** as `move-ticket-authoring-out-of-core`;
coordinate on one arg-materialization mechanism rather than inventing two.
Resolve that, then `relay show` (a pure render of one task's files) is the
simplest first conversion.

## Crux resolution (the design decision)

**The crux is already resolved by a committed, coordinated precedent.** The
ticket asked us to "coordinate on one arg-materialization mechanism rather than
inventing two" with `move-ticket-authoring-out-of-core`. That ticket **landed
as PR #491** and its mechanism is now the ratified pattern (see the parent
umbrella ticket `move-command-logic-to-tickets`, reconciliation note
2026-07-01, and the `coga/extension-model` context, which #491 updated to say
Pass 2 introduces **no new launcher mechanism**).

The committed mechanism, applied to a parameterized read:

> A parameterized stateless read **cannot** become an arg-less launched
> `mode: script` ticket without materializing its transient argument
> (`show <slug>`, `status [dir]` + flags) into a committed file — which the
> files-on-disk / no-transient-launch-params invariant forbids
> (`coga/architecture`, `coga/extension-model` guardrail). So the argument
> stays at the **Typer layer** on a thin command head, and only the *render
> substance* changes home: it moves out of `commands/*.py` into a reusable,
> tested module that is **also exposed in script-step shape** (a `script: run.py`
> skill importing the module). This is exactly what #491 did — `ticket`
> collapsed to a thin head whose deterministic finalize moved to
> `coga.authoring` + the `coga/ticket/finalize` script skill, called inline.

So point 3 of Nico's decision holds and is now *ratified, not merely likely*:
`coga show` **stays** as a thin command entry; the render moves. There is no new
launch mechanism and no transient arg smuggled through a ticket. This also
reconciles the contradiction Nico flagged: the `extension-model` table lists
reads under *External / command* (the command **stays**) while its Pass-2 prose
moves them "into tickets" (the render's **home** becomes a script skill) — both
are true under this shape, and the table row should be reworded in the same PR
(as #491 reworded the `ticket` row).

## Acceptance Criteria

- [ ] The render logic of `coga show` and `coga status` lives in a reusable,
      unit-tested module (proposed `src/coga/views.py`) — **not** in
      `src/coga/commands/show.py` / `status.py`. The substance is relocated
      **unchanged** (no-inversion guardrail): same output, same helpers, no
      deterministic render rewritten as judgment.
- [ ] `src/coga/commands/show.py` and `status.py` shrink to a thin head: parse
      Typer args, `load_config()`, translate `ConfigError` / `TaskNotFoundError`
      / bad-flag to `sys.exit(2)`, then call into `coga.views`. No rendering
      logic remains in the command files.
- [ ] The render has a **script-shaped home**: a `coga/show` script skill
      (`SKILL.md` with `script: run.py`) whose `run.py` imports `coga.views` and
      renders, mirroring `coga/ticket/finalize` and `coga/autoclose/sweep`.
      Shipped in **both** the live `coga/skills/` copy and the packaged
      `src/coga/resources/templates/coga/bootstrap/skills/` copy (CLAUDE.md
      keep-in-sync rule). `status`'s script home is per Open Question 2.
- [ ] `coga show <slug>` and `coga status [dir] [flags]` produce byte-identical
      output to before the move (all flags: `--order-by`, `--reverse`, `--all`,
      `--dirs`, `--blocked`, `--no-recurse`; bootstrap-ref show; empty-repo and
      narrow-terminal cases).
- [ ] Reads stay strictly read-only: `show`/`status` remain in
      `_NON_SWEEPING_COMMANDS` (`cli.py`) and never mutate OS state as a render
      side effect (principle 6).
- [ ] `show`/`status` remain in `_BUILTIN_COMMANDS` — they are **not** aliases
      (an alias is a pure argv rewrite; a read with args + config load + error
      handling needs real code, same finding as #491's `ticket`).
- [ ] New `tests/test_views.py` covers the extracted renders; existing
      `tests/test_status.py` stays green (retargeted at the module where it
      asserted internals).
- [ ] `python -m pytest` green; `coga validate --task
      cli-extension-model/move-read-views-to-tickets-as-scripts --json` clean.
- [ ] The `coga/extension-model` context's reads row/prose is updated in the
      same PR to reflect "thin head + script-shaped render" (per Crux
      resolution and Open Question 3).

## Proposed Shape

Order of work: **`show` first (the proof), then `status`** — the ticket names
`show` (a pure render of one task's files) as the simplest first conversion.
This is one PR's worth; `show` may land as its own commit/PR as the
mechanism proof if the owner prefers.

1. **Extract renders → `src/coga/views.py`** (substance unchanged):
   - `render_show(cfg, task: str, console: Console | None = None) -> None` —
     the body of today's `show.show()` minus arg parsing / `load_config` /
     `sys.exit`. Resolves the target and renders ticket + log.
   - `render_status(cfg, *, directory, no_recurse, order_by, reverse, show_all,
     dirs, blocked, console=None) -> None` — the body of today's
     `status.status()`, with its private helpers (`_format_relative`,
     `_build_table`, `_summary_line`, `_print_blocked`, `_list_dirs`,
     `_done_hint`, `_safe_open_blockers`) moved verbatim.
   - Errors raise a typed `ViewError` instead of `sys.exit`, so the module is
     `typer`-free and unit-testable — exactly how `coga.authoring` raises
     `AuthoringError` and `coga.autoclose` raises `GhError`, leaving exit-code
     translation to the callers.
2. **Shrink the command heads.** `commands/show.py` / `status.py` keep their
   full Typer signatures (the parameter channel — see Crux), do `load_config()`,
   catch `ConfigError` / `TaskNotFoundError` / `ViewError` / bad `--order-by`
   → `sys.exit(2)`, and call the matching `views.render_*`. Nothing else.
3. **Script-shaped home.** Add `coga/skills/coga/show/{SKILL.md,run.py}` (+ the
   packaged bootstrap mirror). `run.py` imports `coga.views` and calls a
   `render_show_from_env(...)` that reads the single target slug from an env var
   (proposed `COGA_VIEW_TARGET`), mirroring `finalize_authored_from_env`'s
   env-contract shape. `show` is the clean single-operand case. `status`'s
   script home is Open Question 2.
4. **Docs/context sync.** Update the `coga/extension-model` reads row/prose per
   the Crux resolution, in this PR.

## Out of Scope

- **`validate`, `skill status`, `recurring list`** — they share this
  destination but the ticket body scopes them out; separate follow-ups.
- **`chat` / `build`** — already aliases (lowest tier); audited by
  `audit-chat-and-build-are-core-free`.
- **`ticket` / `project` / `retire`** — fused *authoring* heads, not reads;
  `ticket` done via #491, the rest are their own follow-ups.
- **Any new launch-time parameter channel or `coga.toml` DSL** — forbidden by
  the no-worse-Typer guardrail; the whole point of the Crux resolution is that
  the arg stays at the Typer layer.
- **Rewriting render logic** — no-inversion: relocate the tested Python
  unchanged; do not "improve" the views while moving them.
- **Physically moving the render body into `coga/skills/**/run.py`** unless the
  owner picks that in Open Question 1 — default keeps tested Python in the
  package (matching #491).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (claude, 2026-07-03)

Dependency check: `remove-the-shim-concept` **landed** (PR #445, merged
2026-06-29) — this ticket is unblocked. The `coga/extension-model` context is
already the post-#445 "tickets-as-scripts" (no "shim") wording, and #491
(`move-ticket-authoring-out-of-core`) landed the shared arg-materialization
mechanism this ticket was told to coordinate on. So the design crux is
*resolved by committed precedent*, not open — see `## Crux resolution` in the
body. Spec is written; no code this step.

Precedents read and mirrored: `coga/ticket/finalize` (SKILL.md + run.py +
`coga.authoring.finalize_authored_from_env`) and `coga/autoclose/sweep`
(run.py → `coga.autoclose.sweep_merged`). Both are deterministic package
Python exposed via a thin `script: run.py` skill — the exact shape `views.py`
+ `coga/show` should take.

## Open Questions

1. **Does "thin head + tested package module + script skill" satisfy your
   'minimize core / make hackable' intent (recommended), or do you want the
   render body physically under `coga/skills/coga/show/run.py`?**
   The parent umbrella ticket's stated win for this group is "the rendered views
   become hackable." Two readings:
   - **(a) #491-faithful (recommended):** render logic → tested
     `src/coga/views.py` (package); a thin `coga/show` `script: run.py` skill
     imports it. Matches #491 exactly, the "coordinate on one mechanism"
     instruction, and the no-inversion guardrail (keep it tested Python).
     Hackability = there is a legible non-kernel entry point you can edit/swap;
     the render internals stay unit-tested in the package.
   - **(b) Fuller relocation:** move the render *body* into
     `coga/skills/coga/show/run.py` so an operator edits the actual rendering in
     `coga/`. Maximizes hackability but sacrifices unit-test ergonomics and
     strains no-inversion. Not recommended, but it's your "minimize core" call.
2. **`status`'s 8-flag surface has no clean script/env parameter channel — OK to
   keep it a thin Typer command over the extracted module, with its script skill
   deferred or default-view-only, while `show` (single operand) gets the full
   script-skill treatment as the proof?** `status`'s `--order-by/--reverse/
   --all/--dirs/--blocked/--no-recurse [DIR]` matrix is precisely the
   "parameterized stateless op whose params belong at the Typer layer" the
   `extension-model` context describes. Env-encoding 8 flags for a `mode: script`
   launch (which passes no argv) is the awkward tail the Crux predicts. `show`
   proves the mechanism; `status` may reasonably stop at "render extracted to
   the tested module, command stays thin."
3. **OK to reword the `coga/extension-model` reads row/prose in the implement
   PR** (from "External / command" to "thin head + script-shaped render"),
   mirroring how #491 reworded the `ticket` row? This closes the contradiction
   you flagged in Decision (2026-06-23) point 1.
4. **Scope confirm:** this ticket = `show` + `status` only.
   `validate`/`skill status`/`recurring list` share the destination but are
   deferred to follow-ups (already stated in the body). Confirm.

## Usage

{"agent":"claude","cache_creation_input_tokens":318955,"cache_read_input_tokens":2394179,"cli":"claude","input_tokens":21225,"model":"claude-opus-4-8","output_tokens":68969,"provider":"anthropic","schema":1,"session_id":"c1a51f10-e7ae-4991-8a2f-7b2ec26595c1","slug":"cli-extension-model/move-read-views-to-tickets-as-scripts","step":"design","title":"Move show/status into their lowest-tier mechanism","ts":"2026-07-04T01:08:04.441234Z","usage_status":"ok"}
