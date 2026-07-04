---
slug: cli-extension-model/move-read-views-to-tickets-as-scripts
title: Move show/status into their lowest-tier mechanism
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/extension-model
- coga/architecture
- coga/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
