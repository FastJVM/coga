---
title: Move show/status into their lowest-tier mechanism
status: draft
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
workflow: null
secrets: null
---

## Description

Per Nico's plan — push each command to the **lowest tier** it can use — move
zach's remaining core read commands out of `commands/*.py`:

- **`show`, `status`** (read-only views) → **tickets-as-scripts** (`mode:
  script`), per Nico's reads decision below. *(The other reads — `validate`,
  `skill status`, `recurring list` — share this destination but aren't the
  immediate focus.)*
- **`chat`, `build`** → **already aliases** (`launch bootstrap/orient` /
  `launch relay-build`) — lowest tier already, no work.
- *(`ticket` → tier-2 shim is already in flight as PR #425 — not part of this.)*

This is **group 1** of `cli-extension-model/move-command-logic-to-tickets`,
independent of #425 and #423. Immediate work: `show` and `status`. Per the
*no-inversion* guardrail the render Python relocates **unchanged**; only its
home changes. Start with `show` (a pure render of one task's files) as the proof.

## Decision (Nico, 2026-06-23)

Reads **do** move to tickets-as-scripts (`mode: script`) — Nico chose
"minimize core" over `extension-model`'s "reads stay commands" rule.
Consequences:
1. `extension-model` now **contradicts** this — it says reads are commands and
   "wrapping these in a task buys nothing." It needs updating to match, or the
   ratified context disagrees with the build (flag to Nico).
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
3. `bootstrap/orient` — the stateless launch shape (no status/log/lock) the
   reads become.
4. The current read commands in `src/relay/commands/` (`show.py`, `status.py`,
   …) — the Python to relocate unchanged.
5. `relay/architecture` — `mode: script` launches and the env vars a script
   step receives (`RELAY_TASK_SLUG`, `RELAY_RELAY_OS_ROOT`, …).

**The crux to settle before writing code:** the reads are *parameterized*
(`relay show <slug>`, `relay status [dir]`), but a stateless script shim is
arg-less. The central question to answer first is *how a parameterized read
hands its argument to a script step* — does it stay a thin command that shells
to a script, reuse the tier-2-shim arg-materialization, or something else?
Resolve that, then `relay show` (a pure render of one task's files) is the
simplest first conversion.
