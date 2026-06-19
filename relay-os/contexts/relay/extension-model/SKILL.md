---
name: relay/extension-model
description: How Relay's command surface is meant to extend — the four tiers (pure alias, declarative shim, workflow, built-in), the irreducible kernel floor, and the determinism×statefulness×when-it-runs axis that decides which tier a command-shaped thing belongs in. Read this before adding a command, an alias, or a shim, or before arguing a built-in should stay one.
---

# Relay extension model

Relay is a microkernel that has not finished drawing its own line. The Python
package (`src/relay/`) is the kernel; almost everything user-facing is — or
could be — a **ticket + workflow + skill** in `relay-os/`. The recurring
question "should this be a built-in command, an alias, or something else?"
keeps recurring because the dividing line was never written down. This context
is that line.

The classification evidence behind it lives in `docs/cli-extension-audit.md`
(a verb-by-verb audit of the current surface). This context is the durable
*rule* that audit produced; read the audit for the worked examples.

## The four tiers

A command-shaped capability sits in exactly one of four tiers. They are ordered
by how much machinery they require — reach for the lowest one that can express
the behavior.

1. **Pure alias** — an argv rewrite in `_DEFAULT_ALIASES` / `[aliases]`
   (`src/relay/cli.py`). Rewritten in `main()` *before* Typer dispatches; there
   is **no hook on either side of the dispatched command**. An alias can only
   express `launch X` / `recurring launch X` shapes that need no pre-logic and
   no post-logic, and it cannot create a ticket. Examples today: `chat` →
   `launch bootstrap/orient`, `dream` → `recurring launch dream`, `build` →
   `launch relay-build`.

2. **Declarative shim** — a config-described `arg → create-draft-with-workflow
   → launch` step. This tier does the *one* thing an alias structurally can't:
   materialize a fresh ticket from a CLI argument and launch a workflow on it.
   It does **not** yet exist as a mechanism — designing it is the subject of
   `cli-alias-line/propose-declarative-shim-mechanism`. Keep its scope to the
   bootstrapping shape only (see the guardrail below).

3. **Workflow** — logic that runs *on an already-existing ticket*, expressed as
   ordered skill steps: `mode: script`, interactive, or a mix. Deterministic
   pre/post work belongs here as **script** steps; agent-facing process (an
   authoring conversation, a decomposition, a retro) belongs here as
   **interactive** steps. Precedent: `autoclose-merged/sweep` is a script step
   calling `relay.automerge.auto_bump_merged`; `digest/post` is a script step
   that runs the `relay digest` consumer.

4. **Built-in command** — irreducible Python in `src/relay/commands/*.py`. The
   *floor*: reserved for behavior that must act before any ticket exists, runs
   outside the ticket model entirely, or needs guarantees the launch/workflow
   machinery can't give (see the floor below).

## The axis: determinism × statefulness × when-it-runs

The tier is not chosen by taste. It falls out of three properties of the work:

- **When does it run** relative to a ticket? *Before a ticket exists* → tier 1
  (if it's a fixed launch) or tier 2 (if it must create one) or tier 4 (if it
  predates the model). *On an existing ticket* → tier 3. *After an agent exits,
  same invocation* → tier 3 script step, or tier 4 if it must be transactional
  with the launch.
- **Is it deterministic?** Deterministic logic (validate, git-sync, a merge
  sweep, a digest post) is safe as a tier-3 **script** step or tier-4 code.
  Non-deterministic, judgment-bearing work (the authoring interview) belongs in
  a tier-3 **interactive** step — never relocate deterministic logic *into* an
  agent step; that trades tested code for prompt execution.
- **Does it hold cross-cutting state / need atomicity?** Secret resolution, the
  git+notify plumbing, and anything that must be all-or-nothing with a launch
  want tier 4, where a single process gives transactional behavior for free.

## The floor — what cannot be a ticket

A workflow runs *on a ticket*, so four kinds of work are structurally stuck in
tier 4 and should stop being argued about:

- **Pre-ticket bootstrapping** that an alias can't do and a shim mechanism
  doesn't yet exist for — the `arg → draft` residue in `relay ticket`,
  `relay project`, `relay retire`. (This is exactly what tier 2 is meant to
  absorb; until it exists, these stay built-ins.)
- **Repo-level scaffolding** — `relay init` creates the `relay-os/` the model
  needs in order to exist.
- **Read-only diagnostics / rendering** — `relay status`, `relay show`,
  `relay validate`. Principle 6 (fail loud) forbids these from mutating state,
  so they can't be ticket-producing.
- **The kernel chokepoints themselves** — `relay launch`/compose, `relay bump`,
  `relay mark`, secret resolution, git transport, notification dispatch. The
  machinery every other tier runs *through*.

Adopt the microkernel as far as the ticket model reaches; keep a deliberately
small built-in floor for what it structurally can't.

## A built-in is not proof it must be one

Most current built-ins are *fused* tiers, not irreducible kernel. `relay
ticket` (~320 lines) is the canonical case: its authoring conversation is a
tier-3 interactive step (the `bootstrap/ticket` shim already), its post-exit
validate + git-sync is a tier-3 script step (same shape as the autoclose
sweep), and only its `arg → draft` bootstrapping is irreducible — a tier-2
residue. When tier 2 exists, `ticket` collapses to a shim + a mixed workflow
with *zero* hand-written command logic. When auditing a built-in, decompose it
this way before concluding it must stay one.

## The guardrail — do not build a worse Typer

The tier-2 shim mechanism earns its place only while it expresses the *single*
fixed shape `arg → create-draft-with-workflow → launch`. The moment it grows
conditionals, computed arguments, or branching, it becomes a mini-DSL in
`relay.toml` — an illegible config language that reimplements Typer worse, and
trades a legible built-in for an opaque layer. That directly violates the
legibility non-negotiable (`relay/principles`). If a capability needs real
branching logic, that logic belongs in a tier-3 **skill**, not in shim config.
Keep the shim declarative-and-dumb; push intelligence into skills or the kernel.

## What this context does NOT cover

- The verb-by-verb classification and the verified pure-passthrough finding —
  see `docs/cli-extension-audit.md`.
- The command reference (what each verb does) — see `relay/cli`.
- The primitives the tiers are built from (tickets, workflows, skills, launch
  composition) — see `relay/architecture`.
- Where the kernel source lives and how to test it — see `relay/codebase`.
