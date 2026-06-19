---
name: relay/extension-model
description: How Relay's command surface is meant to extend — the three homes for logic (kernel, tickets, external tools), aliases as sugar, the launch-rooted kernel (launch plus what it depends on), and the shape test (parameters? state? when does it run?) that decides where a command-shaped thing belongs. Read this before adding a command, an alias, or a shim, or before arguing a built-in must stay one.
---

# Relay extension model

Relay is a microkernel, and this context draws its line. The Python package
(`src/relay/`) is the kernel; almost everything else user-facing is — or should
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
   `mode: script` steps running on a ticket.
3. **External scripts / tools** — *stateless, parameterized* invocations. Two kinds:
   - **External tool** — an existing third-party CLI Relay shells out to (`gh`, `op`,
     `git`). Exists already; Relay calls it and verifies its output (principle 3,
     reuse the OS the operator knows). No mechanism to design.
   - **External script / service** — a *Relay-authored* stateless capability that
     lives outside both the kernel and the ticket model. This home has **no
     mechanism yet**: today a stateless Relay operation can only be a built-in
     command or a `mode: script` ticket step. A first-class surface for it (a `gh`-
     style extension, a separate package/service, or a `relay-os/scripts/` target
     `launch` can call) is a **design target** — the sibling of the tier-2 shim.

## The decision rule

Reach for the lowest tier the *shape* allows — shape decides, not taste:

- **Alias** if it is a fixed argv rewrite (`launch X` / `recurring launch X`) with
  no logic on either side and no ticket to create.
- **External script / tool** if it is a stateless parameterized invocation —
  operands and flags in, effect out, nothing to review. Its parameters live at the
  command (Typer) layer, where arg-parsing is already solved and legible.
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
  factory whose output launch runs) and fresh `init` (creates the `relay-os/` a
  launch needs to exist). A workflow runs *on a ticket*, so neither can be a ticket
  without eating itself.

That is the whole kernel. No other user-facing command is in it — everything a
user or cron calls *to start* a launch is movable.

## The external script / service home

The third home is the least obvious, because its mechanism does not exist yet — it
is a **design target** (`cli-extension-model/design-external-script-service-mechanism`).
The concept is fixed even though the runner is not.

An **external script / service** is a *Relay-authored* stateless capability that
lives outside **both** the kernel and the ticket model. It earns its own home by
elimination:

- **Not kernel** — `launch` never calls it mid-flight; it is not regress/bootstrap
  and not a trust hook.
- **Not a ticket** — it is stateless and parameterized with nothing to review;
  wrapping it in a task is pure ceremony (a dir, status lifecycle, log, broadcast).
- **Not merely an external tool** — Relay authored it. It often *wraps* an external
  tool (the skill installer wraps `gh skill`), but the wrapper is Relay's.

Two flavors, weighted by Relay's local-first stance (principles 3 and 5):

- **External script** — the common case: a small Relay-authored program that runs
  locally — shells out, mutates files, prints. The skill installer is the exemplar,
  and the idiomatic packaging is often a thin wrapper on a CLI the operator already
  has (e.g. a `gh` extension), not a new Python surface.
- **External service** — rare and gated: an out-of-process or hosted crossing.
  Relay stays classical and local-first; v1 has at most one hosted crossing (the
  anonymous telemetry sink — see `relay/architecture`). Prefer a local script unless
  a requirement genuinely needs a hosted endpoint.

Until the mechanism lands, these capabilities live as built-in commands or
`mode: script` steps. This context fixes the *home and its boundary*; the
*mechanism* (how such a script is declared, dispatched, and verified) is left to
the design ticket — deliberately, so we do not pre-build a worse Typer.

## Ticket vs. command: statefulness decides

Both can be parameterized, so the parameter is not the discriminator — **state is**.

- A stateful, reviewable unit of work → **ticket**. `relay retire <slug>` takes a
  slug and creates a *retire task* (retro + PR + delete) — multi-step work that
  wants a blackboard and review.
- A stateless one-shot → **command / external tool**. `relay skill install X`,
  `relay secret get Y`, `relay show <slug>` — operands in, effect out, no state, no
  review. Wrapping these in a task buys nothing and pays the full ceremony of a
  dir, status lifecycle, log, and broadcast.

## Parameters: only if materialized into files

The ticket model has no parameter channel by design, and that is a property to
preserve, not a gap to fill. The load-bearing invariant (`relay/architecture`) is
that **the prompt is a pure function of the files on disk now**.

- A param **materialized into the ticket's files at creation** becomes state — fine,
  and already how `retire`, recurring instantiation, and the tier-2 shim work
  (`arg → draft` writes the arg into the draft).
- A param passed **at launch, per-invocation, not persisted** is forbidden: it
  smuggles hidden input that is not in the repo, so re-running the same slug does
  different things for reasons no file records. That breaks reproducibility and the
  correction loop, and it is the seed of a config DSL (below).

This is why a parameterized *stateless* operation stays a command: its params
belong at the Typer layer, and persisting them would buy nothing for a one-shot.

## Trust boundaries straddle: acquire outside, verify inside

Secrets and skills are trust boundaries, but a trust boundary is not automatically
kernel — it is kernel only at its *mid-flight* hook. The boundary straddles:

- **Acquire — external.** `gh skill` fetches and installs skills; `op` / `env`
  resolve secret values. These are external tools Relay shells out to (a `skill`
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

- **No worse Typer.** Do not add transient launch-time parameters, and do not grow
  the tier-2 shim past the single fixed shape `arg → create-draft-with-workflow →
  launch`. Conditionals, computed args, types, or validation in `relay.toml` rebuild
  Typer worse and in TOML — an illegible config DSL that violates the legibility
  non-negotiable (`relay/principles`). Branching logic belongs in a tier-3 skill.
- **No inversion.** Relocating logic out of the kernel must move the *substance
  unchanged* — `mode: script` Python with its tests intact — never rewrite a
  deterministic check as agent judgment because it now lives "in a skill." Change
  *where it lives and who can edit it*, not *what executes it*.

## The command surface, classified

| Home | Members |
| --- | --- |
| **Kernel** | `launch`/compose · `create`/`draft` primitive · `mark` · `bump` · fresh `init` · *(hooks)* secret-inject, skill-verify-at-compose |
| **Tickets** | already out: `automerge`→sweep, `digest`→post, `delete`→delete-task · move target: `recurring` (scan) · fused, pending tier-2: `ticket`, `project`, `retire` |
| **External / command** | reads: `status`, `show`, `recurring list`, `skill status`, `validate` · external CLI: `skill install/install-local/install-url/update/remove`, `init --update` · notify/escape: `slack`, `panic` · `secret get` |
| **Alias (sugar)** | `chat`, `dream`, `build` · (proposed) `skill-update`, `autoclose` |

## Sequenced externalization, not a redesign

Most of this is already at its floor: the kernel is small, the movable
deterministic logic (`automerge`/`digest`/`delete`) is already a skill or script
step, and the rest is movable-by-choice. There is no system-wide rewrite waiting —
there is a *sequenced* externalization with **three move-types**, justified by
hackability (principle 1: more logic lives as editable `relay-os/` files) and
dogfooding (Relay's own operations exercise the script-step model):

1. **→ ticket / workflow** — mechanism *exists* (`mode: script` steps, the Dream
   pattern). The read views (`status`/`show`/`recurring list`/`skill status`) and
   `recurring` scan move here as stateless script shims / Dream-shaped tasks.
2. **→ ticket via the tier-2 shim** — mechanism *to be designed*
   (`cli-extension-model/propose-declarative-shim-mechanism`). Collapses the
   `arg → draft` heads of `ticket`/`project`/`retire`.
3. **→ external script / service** — mechanism *to be designed* (the surface for
   Relay-authored stateless capabilities, e.g. the skill installer as a `gh`
   extension).

Moves 2 and 3 are sibling design targets; move 1 can proceed independently. Each
respects the carve-outs: the secret/state-write kernel does not move, and
externalized logic stays tested Python.

## What this context does NOT cover

- The verb-by-verb classification and the verified pure-passthrough finding —
  see `docs/cli-extension-audit.md`.
- The command reference (what each verb does) — see `relay/cli`.
- The primitives the homes are built from (tickets, workflows, skills, launch
  composition, the files-on-disk invariant) — see `relay/architecture`.
- Where the kernel source lives and how to test it — see `relay/codebase`.
