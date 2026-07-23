---
name: coga/extension-model
description: How Coga's command surface extends through the kernel, stateful tickets, stateless command tickets, and external tools; aliases are only argv sugar. Read this before adding a command or alias, or before arguing a built-in must stay one.
---

# Coga extension model

Coga is a microkernel, and this context draws its line. The Python package
(`src/coga/`) is the kernel; almost everything else user-facing is — or should
be — a ticket, a skill, or an external tool. The recurring question "should this
be a built-in command, an alias, or something else?" has one answer, derived
below rather than asserted.

The verb-by-verb evidence behind it is `docs/cli-extension-audit.md`; this
context is the durable rule.

## Three homes, plus sugar

Every command-shaped capability has exactly one of three homes for its logic.
Aliases are not a fourth home — they are argv sugar pointing at one of the three.

1. **Kernel** — small, tested Python that cannot be anything else (below).
2. **Tickets / workflows** — *stateful, reviewable* work, expressed as skills and
   script steps running on a ticket.
3. **Stateless commands / external tools** — parameterized invocations with no
   per-run lifecycle:
   - **Command ticket** — a Coga-authored verb defined by a stateless
     `bootstrap/<name>/ticket.md`, implemented by its script or agent body, and
     launched in place. The repo-local definition wins over the packaged
     fallback.
   - **External tool** — an existing third-party CLI Coga shells out to (`gh`,
     `op`, `git`) and whose output Coga verifies.

## The decision rule

Reach for the lowest tier the *shape* allows — shape decides, not taste:

- **Alias** if it is a fixed argv rewrite (`launch X` / `recurring launch X`).
  It supplies a memorable verb but owns no logic.
- **Command ticket / external tool** if it is a stateless parameterized
  invocation — operands in, effect out, no task instance or review lifecycle.
  Use a command ticket for Coga-authored behavior and an existing external tool
  when the operating system already provides it.
- **Ticket / workflow** if it is a stateful, reviewable unit of work — it wants its
  own blackboard, log, and (often) a PR.
- **Kernel** if `launch` calls or depends on it mid-flight, or it must exist before
  any launch can run (below).

## The kernel is `launch` and what it depends on

The kernel is not a taxonomy to memorize — it is **one thing and its dependency
closure**. The kernel is `launch`/compose, plus everything `launch` must call or
depend on while running, plus the bootstrap that must exist before any launch can
run at all. The test for any command is a single question:

> Does `launch` call it *while running*, or does a human/cron call it *to start* a
> launch? Mid-flight → kernel. Kick-off → movable (ticket or external tool).

What that closure contains, and why each is there:

- **`launch` / compose** — the engine itself; everything else runs through it.
- **What launch calls mid-flight** — the `mark` (status) and `bump` (step)
  state-writes it advances, **secret injection** (it resolves and injects values
  into the agent env mid-process), **skill verify-at-compose** (compose *should*
  fail loud when a loaded skill does not match its provenance digest), and notify
  dispatch. *Implementation note:* verify-at-compose is the one kernel hook **not
  yet built** — today the integrity checks live only in the `skill install` path,
  so compose loads skills unverified. It belongs in the kernel; closing the gap is
  outstanding work.
- **What launch consumes / what precedes it** — the `create` primitive (the ticket
  factory whose output launch runs) and fresh `init` (creates the `coga/` a
  launch needs to exist). A workflow runs *on a ticket*, so neither can be a ticket
  without eating itself.

That is the whole kernel. No other user-facing command is in it — everything a
user or cron calls *to start* a launch is movable.

## The stateless command-ticket home

A command ticket is the shipped Coga-authored stateless extension surface. It
uses ticket-format files as a legible **definition**, but it is not a durable
task instance:

- Put the definition under `coga/bootstrap/<name>/ticket.md`; package-backed
  defaults live under the matching bootstrap resource. Resolution is
  local-first, so a repo can mint or deliberately override a verb without a
  core-Python change.
- Give it no `status:` or `workflow:`. `coga launch bootstrap/<name>` runs that
  definition in place each time; it does not create a per-invocation task,
  blackboard, or lifecycle broadcast.
- Use `script:` for deterministic behavior or an agent body when the command
  requires judgment. Keep deterministic checks deterministic when moving them.
- Add an alias such as `open-pr = "launch bootstrap/open-pr"` when the command
  deserves a top-level spelling. Trailing argv continues through the alias.

`open-pr` proved the script-backed form; `resolve-conflicts` proved the
agent-backed form. External third-party tools remain separate: Coga calls
their stable CLI instead of wrapping their implementation in a command ticket.

## Ticket vs. command: statefulness decides

Both can be parameterized, so the parameter is not the discriminator — **state is**.

- A stateful, reviewable unit of work → **ticket**. `coga retire <slug>` takes a
  slug and creates a *retire task* (retro + PR + delete) — multi-step work that
  wants a blackboard and review.
- A stateless one-shot → **command ticket / external tool**. Operands in,
  effect out, no per-run state and no review. A command ticket keeps Coga-owned
  implementation local and editable without paying for a task directory,
  status lifecycle, blackboard, or broadcast.

## Parameters stay explicit

Stateful task parameters and stateless command arguments have different
durability requirements:

- A param **materialized into the ticket's files at creation** becomes state — fine,
  and already how `retire`, recurring instantiation, and the ticket-authoring
  commands work (`arg → draft` writes the arg into the draft). `coga ticket` is
  the example: the command head materializes the title/ref, then the authoring
  interview and finalize phase operate on files.
- A **stateless command ticket** accepts trailing launch arguments without
  persisting them because there is no run state to reproduce. Script-backed
  commands receive `COGA_ARG_1..N` plus `COGA_ARGC`; agent-backed commands
  receive an appended `## Launch arguments` JSON array so ordering and argument
  boundaries remain explicit. The command definition stays in files while the
  invocation stays ordinary, visible argv.
- A stateful workflow must not use that channel as hidden mutable task input.
  Materialize inputs into its ticket instead.

## Trust boundaries straddle: acquire outside, verify inside

Secrets and skills are trust boundaries, but a trust boundary is not automatically
kernel — it is kernel only at its *mid-flight* hook. The boundary straddles:

- **Acquire — external.** `gh skill` fetches and installs skills; `op` / `env`
  resolve secret values. These are external tools Coga shells out to (a `skill`
  acquirer is a thin wrapper on `gh skill` — extractable later as a `gh` extension;
  defer until a second consumer exists or `gh skill` leaves preview).
- **Verify / inject — kernel.** Launch injects a resolved secret into the agent env,
  and compose *should* verify a loaded skill against its digest (the verify hook is
  the one piece not yet built — see the kernel section). Trust is enforced *at the
  moment of use*, not by owning the acquirer.

This ends the "is `secret`/`skill` core?" argument: acquire outside, trust inside.
Secret *values*, in particular, must never flow through the legible
ticket/prompt/blackboard/git machinery — the one place "everything is a ticket"
actively fights the capability boundary.

## Two guardrails

- **No worse Typer.** Keep aliases as fixed argv rewrites and keep command
  argument interpretation in the command ticket. Conditionals, computed args,
  types, or validation in `coga.toml` rebuild Typer worse and in TOML — an
  illegible config DSL that violates the legibility non-negotiable
  (`coga/principles`).
- **No inversion.** Relocating logic out of the kernel must move the *substance
  unchanged* — script-step Python with its tests intact — never rewrite a
  deterministic check as agent judgment because it now lives "in a skill." Change
  *where it lives and who can edit it*, not *what executes it*.

## The command surface, classified

| Home | Members |
| --- | --- |
| **Kernel** | `launch`/compose · `create`/`draft` primitive · `mark` · `bump` · fresh `init` · *(hooks)* secret-inject, skill-verify-at-compose |
| **Stateful tickets** | reviewable work with its own lifecycle, including recurring period tasks, `retire`, and code workflows |
| **Stateless command tickets** | package/repo bootstrap targets such as `open-pr` and `resolve-conflicts`; deterministic or agent-backed, launched in place |
| **External tools** | existing CLIs such as `git`, `gh`, and `op` |
| **Alias (sugar)** | fixed rewrites to launch/bootstrap or other real command targets |

## Migration rule, not a redesign

When a built-in verb is stateless and does not belong to `launch`'s dependency
closure, move its implementation into one command ticket without changing its
semantics:

1. Preserve shared parsers, preflights, and declarative completion gates in the
   kernel when they have other consumers. `open-pr`, for example, moved its
   recipe while `bump` retained the `requires: pr` data gate.
2. Keep tests beside or pointed at the moved implementation and preserve the
   same failure behavior.
3. Expose the bootstrap target directly and add an alias only for a stable
   operator-facing spelling.
4. Do not create a task per invocation. If the work needs a blackboard,
   review, or later handoff, it is stateful work and belongs in an ordinary
   ticket/workflow instead.

## What this context does NOT cover

- The verb-by-verb classification and the verified pure-passthrough finding —
  see `docs/cli-extension-audit.md`.
- The command reference (what each verb does) — see `coga/cli`.
- The primitives the homes are built from (tickets, workflows, skills, launch
  composition, the files-on-disk invariant) — see `coga/architecture`.
- Where the kernel source lives and how to test it — see `coga/codebase`.
