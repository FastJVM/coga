---
name: coga/extension-model
description: How Coga's command surface is meant to extend — the three homes for logic (kernel, tickets, external tools), aliases as sugar, the launch-rooted kernel (launch plus what it depends on), and the shape test (parameters? state? when does it run?) that decides where a command-shaped thing belongs. Read this before adding a command or an alias, or before arguing a built-in must stay one.
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
3. **External scripts / tools** — *stateless, parameterized* invocations. Two kinds:
   - **External tool** — an existing third-party CLI Coga shells out to (`gh`, `op`,
     `git`). Exists already; Coga calls it and verifies its output (principle 3,
     reuse the OS the operator knows). No mechanism to design.
   - **External script / service** — a *Coga-authored* stateless capability that
     lives outside both the kernel and the ticket model. This home has **no
     implementation yet**: today a stateless Coga operation can only be a
     built-in command or a script step on a ticket. A first-class surface for
     it (a `gh`-style extension, a separate package/service, or a
     `coga/scripts/` target `launch` can call) is still to be designed — the
     mechanism design now lives in `docs/cli-extension-external-surface.md`.

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
  factory whose output launch runs) and fresh `init` (creates the `coga/` a
  launch needs to exist). A workflow runs *on a ticket*, so neither can be a ticket
  without eating itself.

That is the whole kernel. No other user-facing command is in it — everything a
user or cron calls *to start* a launch is movable.

## The external script / service home

The third home is the least obvious, because its mechanism is designed but not
implemented yet (`docs/cli-extension-external-surface.md`). The concept is fixed
even though the runner is not.

An **external script / service** is a *Coga-authored* stateless capability that
lives outside **both** the kernel and the ticket model. It earns its own home by
elimination:

- **Not kernel** — `launch` never calls it mid-flight; it is not regress/bootstrap
  and not a trust hook.
- **Not a ticket** — it is stateless and parameterized with nothing to review;
  wrapping it in a task is pure ceremony (a dir, status lifecycle, log, broadcast).
- **Not merely an external tool** — Coga authored it. It often *wraps* an external
  tool (the skill installer wraps `gh skill`), but the wrapper is Coga's.

Two flavors, weighted by Coga's local-first stance (principles 3 and 5):

- **External script** — the common case: a small Coga-authored program that runs
  locally — shells out, mutates files, prints. The skill installer is the exemplar,
  and the idiomatic packaging is often a thin wrapper on a CLI the operator already
  has (e.g. a `gh` extension), not a new Python surface.
- **External service** — rare and gated: an out-of-process or hosted crossing.
  Coga stays classical and local-first; v1 ships zero hosted crossings — Coga
  never phones home (see `coga/principles`). Prefer a local script unless
  a requirement genuinely needs a hosted endpoint.

Until the mechanism lands, these capabilities live as built-in commands or
script steps. This context fixes the *home and its boundary*; the
mechanism design is `docs/cli-extension-external-surface.md` — deliberately a
docs-level implementation contract, so the launch contract does not pre-build a
worse Typer.

## Ticket vs. command: statefulness decides

Both can be parameterized, so the parameter is not the discriminator — **state is**.

- A stateful, reviewable unit of work → **ticket**. `coga retire <slug>` takes a
  slug and creates a *retire task* (retro + PR + delete) — multi-step work that
  wants a blackboard and review.
- A stateless one-shot → **command / external tool**. `coga skill install X`,
  `coga secret get Y`, `coga show <slug>` — operands in, effect out, no state, no
  review. Wrapping these in a task buys nothing and pays the full ceremony of a
  dir, status lifecycle, log, and broadcast.

## Parameters: only if materialized into files

The ticket model has no parameter channel by design, and that is a property to
preserve, not a gap to fill. The load-bearing invariant (`coga/architecture`) is
that **the prompt is a pure function of the files on disk now**.

- A param **materialized into the ticket's files at creation** becomes state — fine,
  and already how `retire`, recurring instantiation, and the ticket-authoring
  commands work (`arg → draft` writes the arg into the draft). `coga ticket` is
  the example: the command head materializes the title/ref, then the authoring
  interview and finalize phase operate on files.
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

- **No worse Typer.** Do not add transient launch-time parameters, and do not let an
  `arg → create-draft-with-workflow → launch` authoring command grow past that single
  fixed shape. Conditionals, computed args, types, or validation in `coga.toml`
  rebuild Typer worse and in TOML — an illegible config DSL that violates the
  legibility non-negotiable (`coga/principles`). Branching logic belongs in a skill.
- **No inversion.** Relocating logic out of the kernel must move the *substance
  unchanged* — script-step Python with its tests intact — never rewrite a
  deterministic check as agent judgment because it now lives "in a skill." Change
  *where it lives and who can edit it*, not *what executes it*.

## The command surface, classified

| Home | Members |
| --- | --- |
| **Kernel** | `launch`/compose · `create`/`draft` primitive · `mark` · `bump` · fresh `init` · *(hooks)* secret-inject, skill-verify-at-compose |
| **Tickets** | already out: `automerge`→sweep, `digest`→post, `delete`→delete-task · `ticket` collapsed to irreducible command head + `bootstrap/ticket` interview + `coga/ticket/finalize` script-shaped module · `recurring` scan collapsed to thin command head + `bootstrap/recurring-scan` stateless script target · move targets: `project`, `retire` |
| **External / command** | reads: `status`, `show`, `recurring list`, `skill status`, `validate` · external CLI: `skill install/install-local/install-url/update/remove` · notify/escape: `slack`, `block`, `unblock` · `secret get` |
| **Alias (sugar)** | `chat`, `dream`, `build` · (proposed) `skill-update`, `autoclose` |

## Sequenced externalization, not a redesign

Most of this is already at its floor: the kernel is small, the movable
deterministic logic (`automerge`/`digest`/`delete`) is already a skill or script
step, and the rest is movable-by-choice. There is no system-wide rewrite waiting —
there is a *sequenced* externalization, organized into **two passes by direction
of movement**, justified by hackability (principle 1: more logic lives as editable
`coga/` files) and dogfooding (Coga's own operations exercise the script-step
model):

- **Pass 1 — what stays *core*, what goes *external*** (design;
  `cli-extension-model/design-external-script-service-mechanism`). Fixes the kernel
  boundary — and closes the not-yet-built verify-at-compose hook — and designs the
  external script/service surface. One decision, because the trust-straddle ties
  "stays kernel" to "becomes an external script."
- **Pass 2 — what goes *into tickets*** (execution;
  `cli-extension-model/move-command-logic-to-tickets`). Moves the read views
  (`status`/`show`/`recurring list`/`skill status`) → stateless script tickets
  (tickets-as-scripts), keeps `recurring` scan behind the stateless
  `bootstrap/recurring-scan` script target, and moves ticket-authoring substance
  out of command files. `ticket` is the first collapsed case: the command head
  still performs the irreducible `arg → draft → launch` hook, while
  deterministic finalization lives in `coga.authoring` and is exposed as
  `coga/ticket/finalize`. `project` and `retire` remain follow-ups; no new
  launcher mechanism is introduced.

Each pass respects the carve-outs: the secret/state-write kernel does not move, and
externalized logic stays tested Python (the no-inversion guardrail).

## What this context does NOT cover

- The verb-by-verb classification and the verified pure-passthrough finding —
  see `docs/cli-extension-audit.md`.
- The command reference (what each verb does) — see `coga/cli`.
- The primitives the homes are built from (tickets, workflows, skills, launch
  composition, the files-on-disk invariant) — see `coga/architecture`.
- Where the kernel source lives and how to test it — see `coga/codebase`.
