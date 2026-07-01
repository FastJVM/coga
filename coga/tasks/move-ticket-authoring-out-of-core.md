---
slug: move-ticket-authoring-out-of-core
title: Move ticket authoring out of core
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
---

## Description

`coga ticket` is a logic-bearing built-in command (`src/coga/cli.py:81`,
`src/coga/commands/ticket.py`, 370 lines). It fuses four responsibilities:
the authoring **interview** (already extracted — it is the `bootstrap/ticket`
skill), plus three pieces of hand-written command logic — **draft-on-the-fly**,
**post-exit validate**, and **git-sync** — behind a **TTY guard**.

This ticket moves the *authoring* substance out of the kernel so `ticket` shrinks
to the smallest thing it can be, with zero hand-written authoring logic living in
the command. It is the real version of what the deleted "tier-2 shim" gestured
at, and the redo of closed PR 425.

The decisive constraint (verified in `docs/cli-extension-audit.md`, the
`cli-extension-model` audit): **`ticket` cannot become a pure alias.** An alias
is a pure argv rewrite with no pre/post hook (`cli.py:247-254`), and
`_validate_aliases` rejects a name that collides with a built-in. Anything that
drafts-on-the-fly, validates after the agent exits, git-syncs changed files, or
guards a TTY needs real code. So the shape is a **collapse to a thin irreducible
head + script-shaped finalize**, not an alias. All four behaviors must survive
the move.

## Context

- **Where the logic lives today** — `src/coga/commands/ticket.py`:
  - `arg → draft` head: `ticket()` + `_resolve_or_create_target` (`:55-152`),
    which calls `create_draft(...)` (`:145`). The audit calls this head
    *irreducible* — `project` and `retire` share the same shape.
  - TTY guard: `_interactive_stdio_has_tty()` (`:196-200`).
  - single-shot interactive spawn of the interview: `spawn_agent_session(...)`
    with the `bootstrap/ticket` skill and the `Begin (…)` kickoff token
    (`:221-237`).
  - post-exit finalize (~200 lines): `_validate_authored_task` (validate +
    workflow-less-draft gate, `:274-302`), `_snapshot_authoring_files` /
    `_changed_authoring_paths` / `_authored_task_refs` / `_support_paths`
    (`:305-356`), and `git.sync_paths(...)` (`:262-271`).
- **The interview is already out of core** — `bootstrap/ticket` SKILL.md +
  the stateless launch target `coga/bootstrap/ticket/ticket.md`. `coga launch
  bootstrap/ticket` already runs the interview, just *without* the three
  kernel behaviors the command wraps around it.
- **Not to be confused:** `src/coga/ticket.py` is the `Ticket` data model
  (frontmatter/body parser), unrelated to the command; it stays put.
- **Script-step precedent to mirror** — `coga.autoclose.sweep_merged`, exposed
  as the `coga/autoclose/sweep` skill via `script: run.py`
  (`coga/skills/coga/autoclose/sweep/SKILL.md`) and run as the sole step of the
  `autoclose-merged/sweep` workflow. That is the exact shape command-grade
  Python takes once it leaves the kernel.
- **Dependencies / redo** — assumes the shim-concept removal
  (`remove-the-shim-concept`) has landed so the model is clean. PR 425 attempted
  this and is being closed; redo from scratch (its approach is a reference, not a
  base — see Open Questions).
- Keep `python -m pytest` green; the `ticket` behavior is covered by
  `tests/` (and alias behavior by `tests/test_aliases.py`).

## Acceptance Criteria

- [ ] No authoring logic (interview orchestration, validate, git-sync) is
      hand-written inside `src/coga/commands/ticket.py`. What remains is the
      irreducible `arg → draft` head, the TTY guard, and the spawn of the
      interview session.
- [ ] The post-exit **validate + workflow-less-draft gate + git-sync** logic
      lives in a reusable, unit-tested module (proposed `src/coga/authoring.py`)
      — not in the command file — and is exposed in the script-step shape (a
      skill carrying `script:` that imports and calls the module, mirroring
      `coga/autoclose/sweep`).
- [ ] All four preserved behaviors still hold, verified by tests:
      draft-on-the-fly (`coga ticket "New title"` scaffolds a draft),
      post-exit validate (a schema-broken authored ticket exits non-zero),
      workflow-less-draft gate (a draft left with no workflow exits non-zero),
      git-sync (changed `tasks/`/`contexts/`/`skills/` are committed), and the
      TTY guard (non-TTY interactive launch is refused).
- [ ] `ticket` is **not** an alias and does not collide with the alias
      validator; `_BUILTIN_COMMANDS` still lists it.
- [ ] The stateless, concurrent-safe property of `coga launch bootstrap/ticket`
      is not regressed (no new lock/step state introduced on the shared
      bootstrap launch target) — unless the owner explicitly picks the
      workflow-step option in Open Questions.
- [ ] `python -m pytest` is green; `coga validate --json` passes.
- [ ] If any shipped context/doc describes `ticket` as fused kernel logic
      (e.g. `docs/cli-extension-audit.md`, `coga/extension-model`), it is
      updated in the same PR to reflect the collapse.

## Proposed Shape

Recommended mechanism (Option A — see Open Questions for the fork):

1. **Extract finalize into `src/coga/authoring.py`.** Move the post-exit
   logic verbatim (no behavior change — audit guardrail: "move the substance
   unchanged"): `snapshot_authoring_files(cfg)`, `changed_authoring_paths(...)`,
   `authored_task_refs(...)`, `support_paths(...)`, `authoring_sync_message(...)`,
   `validate_authored_task(cfg, ref)`, and a top-level
   `finalize_authored(cfg, *, before_snapshot, ref) -> None` that runs
   validate + the workflow-less-draft gate + `git.sync_paths(...)`. Add unit
   tests (`tests/test_authoring.py`) covering each behavior.
2. **Expose finalize in script-step shape.** Add skill
   `coga/skills/coga/ticket/finalize/SKILL.md` with `script: run.py`; `run.py`
   imports `coga.authoring` and calls `finalize_authored`, exactly mirroring
   `coga/autoclose/sweep`. This is what makes the finalize a *ticket/script*
   home rather than kernel — even if Option A calls the module inline, the
   logic now has a legitimate non-kernel entry point.
3. **Shrink `commands/ticket.py` to the head.** Keep `ticket()`,
   `_resolve_or_create_target`, `_resolve_existing`, `_authoring_ticket`, the
   TTY guard, and the single-shot `spawn_agent_session(...)`. Take the
   before-snapshot via `coga.authoring.snapshot_authoring_files` and, after the
   session, call `coga.authoring.finalize_authored(...)`. The ~200 lines of
   inlined finalize helpers are deleted from this file (now imported). Target:
   command file roughly halves and contains no authoring logic of its own.
4. **Docs/context sync.** Update `docs/cli-extension-audit.md` and the
   `coga/extension-model` context so the `ticket` row/example reflects "head +
   extracted script-shaped finalize" instead of "fused built-in."

Order of work: (1) extract + tests green → (2) skill wrapper → (3) rewire
command + delete inlined helpers → (4) docs. Each step keeps `pytest` green.

## Out of Scope

- **Making `ticket` a pure alias** — audit-verified impossible; do not attempt.
- **Touching the interview content** — the `bootstrap/ticket` SKILL.md and the
  `coga/bootstrap/ticket/ticket.md` launch target are already out of core;
  no changes beyond what the collapse strictly requires.
- **Collapsing `project` / `retire`** — they share the same irreducible head
  but are separate tickets.
- **The `create` legacy alias** (`create = "launch bootstrap/ticket"`) and the
  `create` built-in — untouched.
- **`src/coga/ticket.py` (the `Ticket` model)** — untouched.
- **Introducing new launch-time parameters or a `coga.toml` DSL** — the head
  stays the single fixed `arg → draft → launch` shape (audit guardrail #1).

<!-- coga:blackboard -->

## Decisions

- **Mechanism fork resolved → Option A (inline finalize).** nick's call. The
  thin `ticket` head calls `coga.authoring.finalize_authored(...)` *inline*
  after the single-shot interview session, preserving today's stateless,
  concurrent-safe authoring (no lock, no `step:` transitions on the shared
  bootstrap launch target). The finalize logic is "out of core" as a reusable,
  tested, script-exposed module (`coga.authoring` + `coga/ticket/finalize`
  skill) — the command no longer *contains* authoring logic, it just calls the
  module. Option B (finalize as a bumped workflow step) is rejected: its extra
  statefulness would break the lockless bootstrap-ticket design for little gain.
- **Workflow switched `code/design-then-implement` → `code/with-review`.**
  nick's call, so the ticket executes now that the spec is written. The spec
  in the body feeds the `implement` step directly (no separate design step);
  `peer-review` runs the other agent (codex) over the diff before the PR.

## Notes for implement

- **PR 425** is a *reference, not a base* ("redo from scratch"). Run
  `gh pr view 425` / `gh pr diff 425` early to avoid repeating whatever got it
  closed.
- **Dependency:** assumes `remove-the-shim-concept` has landed and the model is
  clean. Confirm before starting; if it hasn't merged, the "collapse a built-in"
  framing may not match the tree — `coga block` rather than guess.
- Reassigned owner/human `zach → nick` at nick's request (agent/assignee stay
  `claude`). Frontmatter edits sync on the next state transition.
- Confirmed the work is **not started**: `ticket` is still a fused built-in
  (`cli.py:81`, `commands/ticket.py`), no `ticket` alias in `coga.toml`.
