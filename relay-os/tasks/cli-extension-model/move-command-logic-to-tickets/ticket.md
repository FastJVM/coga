---
title: Move command logic into tickets
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- relay/extension-model
- relay/architecture
- relay/codebase
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
step: 1 (execute)
---

## Description

**Part of `cli-extension-model/` — Pass 2 (execution: `→ ticket`). Companion to
`design-external-script-service-mechanism` (Pass 1: the core boundary + the
`→ external` design). The two are one decision split by direction: Pass 1 fixes
what stays *core* and what goes *external*; this ticket moves the command logic
that belongs *in tickets* there.**

Per `relay/extension-model`, relocatable command logic should live as skills and
`mode: script` steps on a ticket, not hand-written `commands/*.py`. Three groups
move here, in dependency order:

1. **Reads → stateless script shims** *(mechanism exists)*. `status`, `show`,
   `recurring list`, `skill status` become read-only script shims (the
   `bootstrap/orient`-style stateless launch shape — no status, no log, no lock).
   Mechanical relocation; the win is the rendered views become hackable.
2. **`recurring` scan → a Dream-shaped task** *(mechanism exists)*. The
   scan/orchestration body becomes a recurring task that calls the `create` +
   `launch` kernel primitives — exactly the shape Dream already uses.
3. **Fused heads → workflow, via the tier-2 shim** *(mechanism to build here)*.
   The `arg → draft` heads of `ticket`/`project`/`retire` collapse onto a
   **declarative shim**: a config-driven `arg → create-draft-with-workflow →
   launch` step that does the one thing an alias can't — materialize a ticket from
   a CLI argument. This is the *only* new mechanism Pass 2 needs; build it, then
   move the heads.

The tier-2 shim, sketched:

```toml
[shims.ticket]
launch = "bootstrap/ticket"
draft_if_missing = true
validate_after = true
sync = ["tasks", "contexts", "skills"]
require_tty = true
```

Cover: the shim's declarative schema; how dispatch changes in `cli.py` (`main()`
rewrites argv pre-Typer today — the shim needs a real around-hook); which commands
migrate (`ticket`, then `project`/`retire`); what stays bespoke; and the order
(reads + `recurring` first — no mechanism needed; heads last — gated on the shim).

**Guardrails** (from `relay/extension-model`): *no inversion* — relocate the tested
Python **unchanged** into script steps, never rewrite a deterministic check as
agent judgment because it now lives "in a skill." *No worse Typer* — the shim stays
the single fixed shape `arg → draft + workflow → launch`; conditionals or computed
args make it an illegible `relay.toml` DSL, so branching logic belongs in a skill,
not shim config.

Done = the reads + `recurring` moved (or a committed plan + first move), plus a
committed design for the tier-2 shim with the fused-head migration path. Building
the shim runner / moving the heads can be follow-ups gated on the shim design.

## Context

- The rule this executes: `relay/extension-model` — the three homes, the
  "sequenced externalization" section (this is Pass 2 / `→ ticket`), and the two
  guardrails. Read it first.
- The shim exemplar to subsume: `src/relay/commands/ticket.py` (~320 lines) —
  enumerate the pre/post behaviors the shim must express (`create_draft` on missing
  target, post-run `validate_task_dir` + workflow gate, snapshot/diff/git-sync of
  `tasks/contexts/skills`, TTY check). `relay ticket` was the `create = "launch
  bootstrap/ticket"` alias before promotion — the shim is "alias ergonomics back
  without losing the logic that forced the promotion."
- Why a plain alias can't do the heads: `src/relay/cli.py` `main()` rewrites argv
  *before* Typer dispatches — no after-hook. The shim adds the around-hook.
- The already-out precedents for moves 1–2: `automerge` → `autoclose-merged/sweep`,
  `digest` → `digest/post` (deterministic logic already runs as script steps).
- Companion: `design-external-script-service-mechanism` (Pass 1) owns the core
  boundary + the `→ external` design. `add-recurring-launch-aliases` is independent
  alias sugar.

**Out of scope:** the `→ external` work (Pass 1), and anything touching the kernel
carve-outs (secret resolution and the `mark`/`bump` state-writes stay core).
