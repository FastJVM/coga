---
slug: cli-extension-model/move-command-logic-to-tickets
title: Move command logic into tickets
status: in_progress
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- coga/extension-model
- coga/architecture
- coga/codebase
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## State reconciliation (2026-07-01, claude) — read this first

**PR #491 (`move-ticket-authoring-out-of-core`, landed today) supersedes the
tier-2 TOML shim below.** It collapsed `ticket.py` to its irreducible head
(`arg → draft → launch`) with deterministic finalization extracted to
`coga.authoring` + the script-shaped `coga/ticket/finalize` skill, and updated
`coga/extension-model` to say Pass 2 introduces **no new launcher mechanism**.
That resolves the OPEN question below as option (a), taken further: no
declarative `[shims.*]` config at all — irreducible head + script-shaped module
is the committed fused-head pattern. `project`/`retire` remain follow-ups on the
same pattern (bespoke create-step, shared frame).

**Where the three groups now live** (this ticket has become an umbrella —
each group was split out or landed elsewhere):
1. **Reads** → child ticket `cli-extension-model/move-read-views-to-tickets-as-scripts`
   (draft, `code/design-then-implement`, carries Nico's 2026-06-23 direction
   decision + the parameterization crux for its design step). Its stated
   dependency `remove-the-shim-concept` LANDED (PR #445, merged 2026-06-29), so
   it is unblocked. Mechanism gap its design must solve: `launch.py:267-268`
   refuses script launches on bootstrap tickets, and reads are parameterized
   (`show <slug>`) while the no-transient-launch-params guardrail stands.
2. **Recurring scan → Dream-shaped task** — the one group with NO ticket and
   no work yet.
3. **Fused heads** — `ticket` DONE via #491 (pattern above); `project`/`retire`
   follow-ups on the same pattern, no tickets yet.

Also noticed: sibling draft `cli-extension-model/rename-shim-to-alias` is stale
(pre-dates PR #445, which deleted the shim concept it wanted to rename;
references dead PR #425 and old "Relay" naming) — candidate for deletion.

## Tier-2 shim design (2026-06-23, zach + claude) — SUPERSEDED by PR #491, kept for the audit trail

The "committed design" the Done= asks for. ELABORATES Nico's sketch in the ticket
body; does not change it. Scope: the GENERIC `arg → create-draft → launch`
mechanism. Greet-first is NOT here — Nico built it in PR #423 (see "Relationship").

### 1. The shim's declarative schema (Nico's sketch, verbatim)
```toml
[shims.ticket]
launch = "bootstrap/ticket"
draft_if_missing = true
validate_after = true
sync = ["tasks", "contexts", "skills"]
require_tty = true
```
Each field = one tested `ticket.py` behavior:
- `launch` — the authoring entry to launch. **Routes through `spawn_agent_session(...)`**,
  the single shared spawn path PR #423 built; per-command options
  (discussion / kickoff / secrets-env / prompt_suffix) are arguments to it.
- `draft_if_missing` — `create_draft(arg)` when arg isn't an existing ticket.
- `validate_after` — post-session `validate_task_dir` + the draft-must-have-a-workflow gate.
- `sync` — snapshot/diff/git-sync of tasks/contexts/skills.
- `require_tty` — the interactive-TTY check.

### 2. Dispatch — the cli.py around-hook
`cli.py main()` rewrites argv BEFORE Typer today — there is no after-hook. The shim
needs a real **around-hook**: for a shim-name command, resolve arg →
(draft_if_missing) → launch → validate_after + sync. This is the ONE new mechanism
Pass 2 builds.

### 3. Which commands migrate
`ticket`, then `project`, then `retire` — BUT see §4: only `ticket` fits cleanly.

### 4. What stays bespoke (analysis 2026-06-23, read ticket.py/project.py/retire.py)
The three "fused heads" LOOK alike but their `arg` means three different things, so
only ONE fits the shim's `arg → create-draft-from-arg → launch` shape:

| Command | the `arg` is… | creates… | fits `draft_if_missing`? |
|---|---|---|---|
| `ticket`  | the new title (or existing slug) | one draft, from the arg | YES — clean fit |
| `project` | a *seed* for a brainstorm | many drafts, by the *skill* | NO — shim creates nothing |
| `retire`  | an existing *done* task | a separate fixed-template wrapper task | NO — arg must exist |

Shared (→ runner / fields): config load, resolve target, TTY check (`require_tty`),
spawn (now `spawn_agent_session`, post-#423), post-validate (`validate_after`), `sync`.
Tier-3 skills (untouched): the `ticket`/`project` interviews, the `retro` skill.

Bespoke residue:
- `ticket`: ~none. Edit-existing status check + in_progress/done caution + workflow
  gate are deterministic → shared-runner Python / `validate_after`.
- `project`: the seed handling (appended to the prompt, NOT materialized — check vs
  the params-into-files rule), drafts created by the skill (`draft_if_missing` off),
  and it validates a new SET of drafts, not one target.
- `retire`: the "must exist + be done" precheck and the fixed-template wrapper-task
  create (not draft-from-arg).

**OPEN — for Nico:** the shim fits `ticket`; `project`/`retire` share only the outer
frame (resolve → [create *something*] → launch → validate/sync) and differ in the
"create" step. Either (a) keep the shim ONE fixed shape (= `ticket`'s) and let
`project`/`retire` keep their distinct create-logic as bespoke Python on the shared
frame, or (b) give the shim a flexible "create" step — which risks "no worse Typer".
The guardrail points at (a). His call.

### 5. Order (Nico's)
- **First (no new mechanism):** reads → stateless script shims
  (status / show / recurring list / skill status); `recurring` scan → Dream-shaped task.
- **Last (gated on the shim):** the fused heads — `ticket`, then `project` / `retire`.

### Guardrails (from relay/extension-model)
- **No inversion** — relocate the tested Python UNCHANGED; never rewrite a
  deterministic check as agent judgment.
- **No worse Typer** — keep the single fixed shape `arg → draft → launch`; no
  conditionals / computed args / validation in `relay.toml`.

### Relationship to greet-first / the launch mechanism (UPDATED post-PR #423)
Greet-first + the launch-consolidation are DONE by Nico in **PR #423**
(`agent-session-options`), which **supersedes #417** and **closes
`finish-relay-ticket-greet-first-land-pr-417`**. It routes `launch`/`ticket`/`project`
through ONE shared spawn, `spawn_agent_session(...)`, with per-command differences
(greet-first `kickoff="Begin"`, secrets-env, discussion, `project`'s seed via
`prompt_suffix`) as explicit arguments.

What this means here: #423 built the consolidated spawn path the shim's `launch` step
routes through — it touched only the SPAWN (compose → spawn → log), NOT the front
(`arg → create-draft`) or back (`validate/sync`) this shim owns. So the shim's scope
is unchanged and its launch dependency is now built. Greet-first is no longer in this
ticket's scope (the earlier "shim first → greet-first second" plan is moot).
