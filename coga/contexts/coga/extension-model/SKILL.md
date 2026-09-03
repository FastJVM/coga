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
2. **Tickets / workflows** — *stateful, reviewable* work. A ticket may run a
   deterministic `ticket.py` phase, an agent phase, or both in that order.
3. **Stateless commands / external tools** — parameterized invocations with no
   per-run lifecycle:
   - **Command ticket** — a Coga verb defined by a stateless
     `bootstrap/<name>/ticket.md`, with either an agent body or a deterministic
     `ticket.py` sibling. The repo-local definition wins over the packaged
     fallback.
   - **External tool** — an existing third-party CLI Coga shells out to (`gh`,
     `op`, `git`) and whose output Coga verifies.

## The decision rule

Reach for the lowest tier the *shape* allows — shape decides, not taste:

- **Alias** if it is a fixed argv rewrite (`launch X` / `recurring launch X`).
  It supplies a memorable verb but owns no logic.
- **Registered recipe, command ticket, or external tool** if it is a stateless
  parameterized invocation—operands in, effect out, no task instance or review
  lifecycle. Use a registered recipe for a repository-independent deterministic
  Coga command contract, a command ticket for repo-extensible behavior (agent
  judgment or a no-operand `ticket.py`), and an existing external tool when the
  operating system already provides it.
- **Ticket / workflow** if it is a stateful, reviewable unit of work — it wants
  its own blackboard, log, and (often) a PR. Its deterministic half can live in
  a `ticket.py` sibling without acquiring a kernel registry entry.
- **Kernel** if `launch` calls or depends on it mid-flight, it must exist
  before any launch can run, it is one of the deliberately fixed deterministic
  commands registered behind `coga run` (below), or its reviewed contract names
  a package-private invariant that requires the command and kernel to be
  versioned together (below).

## The kernel is the launch closure, fixed recipes, and proven command code

Most of the kernel is not a taxonomy to memorize — it is **one thing and its
dependency closure**. The kernel is `launch`/compose, plus everything `launch`
must call or depend on while running, plus the bootstrap that must exist before
any launch can run at all. For ordinary command-surface decisions, ask:

> Does `launch` call it *while running*, or does a human/cron call it *to start* a
> launch? Mid-flight → kernel. Kick-off → movable (ticket or external tool).

There are two explicit exceptions. The first is `coga run <recipe>`, which
exposes a closed, in-package name-to-function table for deterministic jobs
whose argv, output, and exit behavior are part of Coga's command contract.
Those registered functions are real Python command implementations, not aliases
or discovered skill plugins, so they also live in focused core modules. Adding
a name is a reviewed kernel change; repository-local tickets and skills cannot
extend the table.

The second is a **proven co-versioned command implementation**. It stays in the
kernel even when no launch depends on it only when its reviewed contract names
the exact package-private invariant or atomic transaction it enforces and shows
why an edge command using Coga's stable CLI and files-on-disk interfaces cannot
preserve that invariant. This is the same narrow rule `coga/codebase`,
`AGENTS.md`, and `CLAUDE.md` state for `src/coga/`; the launch closure is its
common case, not its whole extent. Python logic only proves that a verb is not
an alias. Operands, validation, Coga-file access, or an implementation already
living in `src/coga/` do not distinguish a kernel command from a command ticket
or independently versioned external CLI. A verb whose whole body starts a
launch is still an alias however it is spelled. `coga digest`
(`commands/digest.py`) and `coga megalaunch` (`megalaunch.py`) are current
in-package implementations, not ratified examples of this exception: the
active command-cleanup design ticket must either record the required
co-versioning proof or migrate each command where its shape allows.

What that closure contains, and why each is there:

- **`launch` / compose** — the engine itself. Launch classifies the one target
  directory before composition, subprocesses its `ticket.py` when present, and
  composes only if that deterministic phase leaves agent work open.
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

That is the launch dependency closure. Outside it and the two exceptions
above, a user-facing command that merely starts a launch remains movable.

## The stateless command-ticket home

A command ticket is the repo-extensible Coga-authored stateless surface. The
fixed `coga run` table is intentionally not an extension mechanism. A command
ticket uses ticket-format files as a legible **definition**, but it is not a
durable task instance:

- Put the definition under `coga/bootstrap/<name>/ticket.md`; package-backed
  defaults live under the matching bootstrap resource. Resolution is
  local-first, so a repo can mint or deliberately override a verb without a
  core-Python change.
- Give it no `status:` or `workflow:`. `coga launch bootstrap/<name>` runs that
  definition in place each time; it does not create a per-invocation task,
  blackboard, or lifecycle broadcast.
- With only `ticket.md`, a command ticket composes a prompt and launches an
  agent. With the exact sibling `ticket.py`, launch subprocesses that file
  directly, with no task lifecycle or blackboard writes and no agent. The
  deterministic v1 entry point receives no operands.
- Recurring `delegate: bootstrap/<name>` deliberately names only the
  agent-backed form. Its purpose is to remove an agent wrapper around another
  agent launch. A script-backed target is rejected before period creation;
  deterministic recurring behavior belongs in the recurring template's own
  `ticket.py`, which is copied into the period task. A materialized period may
  not carry both that copied script and a frozen `delegate:` field.
- Add an alias such as `resolve-conflicts = "launch bootstrap/resolve-conflicts"`
  when the command deserves a top-level spelling. Trailing argv continues
  through the alias.

`resolve-conflicts` is the shipped agent-backed form. `open-pr` is a registered
`coga run` recipe: a fixed name in `runner.RECIPES` is a genuine package
command with a repository-independent argv/stdout/exit-code contract. A
ticket-owned deterministic operation instead stays beside its command ticket.
External third-party tools remain separate: Coga calls their stable CLI instead
of wrapping their implementation in a command ticket.

## The ticket-owned deterministic phase

The classifier is deliberately smaller than a plugin mechanism. For the one
target already selected, launch stats the exact sibling `ticket.py`; it never
scans a tree, discovers capabilities, imports edge modules, or consults a
frontmatter mode. Core subprocesses the file as
`[sys.executable, <path-to-ticket.py>]` and never imports from a ticket or
skill directory. Only that reserved name changes dispatch. A `run.py`, a test
helper, or any other script attachment remains an ordinary file unless agent
instructions invoke it explicitly.

For a stateful ticket, `ticket.py` runs once per workflow step. If it completes
the step through `coga bump`, `coga mark done`, or `coga block`, launch observes
the new frontmatter and does not spawn an agent for that step. If it exits zero
while the step remains open, launch composes the freshly re-read ticket — so a
blackboard append is the visible handoff — and starts the agent on the same
step. A nonzero exit halts before composition and remains the reported and
audited result even when the script deleted or malformed its ticket. A removed
entry point falls through as agent-only work. A step advance repeats
`ticket.py` only while control stays with a configured agent; a human or
unassigned handoff stops the chain. This completion contract makes a forgotten
completion fail toward running the agent, never toward silently skipping
judgment.

That is the whole extension-model contract: which filename changes dispatch,
and what an exit code means for composition. What a strict human assist must
prove around that script phase — the pre-execution publication lease, the exact
post-child byte snapshot, the fresh inherited lease each in-script lifecycle
command consumes, task validation before publication, and the sync boundaries
that force config, ticket, secrets, and the entry-point stat to be re-derived —
lives in `coga/launch-internals`, and is not restated here.

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
- An **agent-backed stateless command ticket** accepts trailing launch
  arguments without persisting them because there is no run state to
  reproduce. The agent receives an appended `## Launch arguments` JSON array
  so ordering and argument boundaries remain explicit. A deterministic
  `ticket.py` receives no operands in v1; use a registered recipe or external
  tool when a stable parameterized command contract is required.
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
  unchanged*: deterministic Python stays Python, either as a registered recipe
  or a ticket-owned `ticket.py`; never rewrite a deterministic check as agent
  judgment merely because its invocation is documented by a skill. Change
  *where it lives and who can edit it*, not *what executes it*.

## The command surface, classified

| Home | Members |
| --- | --- |
| **Kernel** | `launch`/compose · `create`/`draft` primitive · `mark` · `bump` · fresh `init` · fixed `coga run` recipes · commands proven to require co-versioning with a named package-private invariant · *(hooks)* secret-inject, skill-verify-at-compose |
| **Stateful tickets** | reviewable work with its own lifecycle; may run `ticket.py`, an agent, or both |
| **Stateless command tickets** | package/repo bootstrap targets such as `resolve-conflicts`; agent-backed or no-operand `ticket.py`, launched in place |
| **External tools** | existing CLIs such as `git`, `gh`, and `op` |
| **Alias (sugar)** | fixed rewrites to launch/bootstrap or other real command targets |

The table names home criteria and settled primitives; it does not ratify every
current `src/coga/` verb as a permanent kernel member. Several live verbs are
still under classification — including `digest` and `megalaunch` — and may
move when their reviewed shape permits it. `docs/cli-extension-audit.md` holds
the current verb-by-verb inventory; an active migration ticket remains
authoritative about decisions it was created to settle.

## Migration rule, not a redesign

When a built-in verb is stateless, does not belong to `launch`'s dependency
closure or the fixed recipe table, and has no reviewed co-versioning proof,
move its implementation to the appropriate edge without changing its
semantics:

1. Preserve shared parsers, preflights, and declarative completion gates in the
   kernel when they have other consumers. `open-pr`, for example, moved its
   recipe out of the command head while `bump` retained the `requires: pr`
   data gate.
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
- The strict publication invariants around a `ticket.py` phase and around
  launch generally — leases, recorded-checkout and PR-head proofs,
  compare-and-set publication, compensation — see `coga/launch-internals`.
