---
name: relay/architecture
description: Mental model for relay — primitives, planes, composition. What an agent needs to know to reason about how relay works as a system.
---

# Relay architecture

Relay is a markdown-first, git-backed company OS. Everything an agent
operates on is a file in `relay-os/`. There is no database, no daemon,
no in-memory state.

## Primitives

- **Tickets** live in `relay-os/tasks/<slug>/` as a directory. Each has
  `ticket.md` (frontmatter + body), `log.md` (append-only, written by
  CLI commands only), and `blackboard.md` (free-form workspace shared
  between human and agent).
- **Contexts** are domain knowledge — what's true about the world.
  Project-local contexts live in `relay-os/contexts/`; bundled Relay
  batteries live in `relay-os/bootstrap/contexts/`. Attached to tickets via
  `contexts:` frontmatter list. Local contexts override bundled contexts with
  the same ref.
- **Skills** are process knowledge — how to do a thing. Project-local skills
  live in `relay-os/skills/`; bundled Relay batteries live in
  `relay-os/bootstrap/skills/`. Attached to **workflow steps**, not tickets.
  Local skills override bundled skills with the same ref. The `skills:`
  ticket-level frontmatter field exists for skill refs that apply to the
  ticket as a whole; `bootstrap/ticket` is the authoring interview and must
  never appear there — `relay ticket` injects it into the launch prompt
  only, never persists it on the ticket.
- **Workflows** are ordered step definitions. Live in
  `relay-os/workflows/`. Frozen into a ticket's frontmatter at
  creation — in-flight tickets are unaffected by later workflow edits.
  Each step may declare an `assignee:` role token (`owner` | `human` |
  `agent` | `other-agent`); on bump, the token resolves against the ticket's
  matching role field and rewrites `assignee:`. `other-agent` resolves to the
  peer agent (it needs two configured `[agents.*]`) and drives peer-review
  flips (e.g. `code/with-review`) and agent-rotation relaunches. Steps without
  one leave the assignee unchanged.
- **Recurring templates** live in `relay-os/recurring/`. `relay recurring`
  scans them, scaffolds the current period's task for each, and launches the
  due ones; the created tasks then use the same ticket, workflow, launch,
  bump, and blackboard machinery as any other task.
- **Bootstrap shims** in `relay-os/bootstrap/<name>/ticket.md` are
  stateless launch targets for skills. No status, no workflow. Used for
  ticket-less re-entry points like `relay launch bootstrap/orient`
  (the `chat` alias). They are never factories — `relay launch` no
  longer scaffolds new tickets from shims; use `relay create` for that.
- **Bundled batteries** are package-backed skills, contexts, hooks, and launch
  shims materialized under `relay-os/bootstrap/` by `relay init` and
  `relay init --update`. `pip install relay-os` puts them in the wheel; init
  materializes them into each repo. They are inspectable local files, but
  edits under `bootstrap/` are overwritten on update. Copy a skill or context
  to the matching `relay-os/skills/` or `relay-os/contexts/` ref to override it.
- **Dream** is Relay's generic ticket cleanup pass. It is a recurring task
  template (`relay-os/recurring/dream/`) plus a `dream` alias — not a
  built-in command. `relay recurring` scaffolds and launches it when its
  weekly schedule is due; the `relay dream` alias (`recurring launch dream`)
  scaffolds and launches it on demand. The parent task orchestrates child `mode: script`
  tasks over worker skills; its body scans the ticket set, runs fixed Relay
  housekeeping skills, proposes cleanup, and writes reviewable results to its
  blackboard.
- **REM** is repo/user-specific recurring maintenance. A REM run is an
  ordinary recurring task whose body defines that repo's operational checks,
  domain skills, output conventions, and review gates.

Contexts and skills both use the SKILL.md format (frontmatter `name`
+ `description`, then body). Zero proprietary extensions — same format
Claude Code and Codex use.

## Canonical ticket frontmatter

Every ticket carries the same canonical key set. These names are
reserved — no extension or alias may collide with them:

`title`, `status`, `mode`, `owner`, `human`, `agent`, `assignee`,
`watchers`, `workflow`, `step`, `contexts`, `skills`.

A repo may declare additional fields under `[ticket.fields.<name>]` in
`relay.toml` — see "Ticket frontmatter extensions" below.

## Ticket frontmatter extensions

Per-repo frontmatter fields are declared in `relay.toml`:

```toml
[ticket.fields.docket]
description = "USPTO docket number"

[ticket.fields.priority]
description = "P0/P1/P2 triage tier"
values = ["P0", "P1", "P2"]
default = "P2"
required = true
```

Each declaration accepts four keys: `description` (required string),
`values` (optional enum), `default` (optional string), `required`
(optional bool). No other keys, no nesting, no types beyond string.

Three mechanisms honor the spec:

- `relay draft` / `relay ticket` write every declared field into the new
  ticket below the `# --- extensions ---` marker, seeded with the
  declared default (or `""`).
- `relay validate` enforces the schema — declared-but-missing fails
  loud; an enum violation fails loud; an undeclared key not in the
  canonical set is treated as an orphan (warn-only) so removing an
  extension is symmetric.
- `relay mark active` refuses to activate a ticket whose `required`
  fields are empty.

Extensions live in the same frontmatter the prompt composer already
reads, so no extra layer is needed — the field is in every composed
prompt by virtue of being on the ticket.

## Workflow gated at activation, not draft time

`relay draft` (and its compatibility spelling `relay create`) take an
*optional* `--workflow <name>`. A workflow-less draft is a valid authoring
state — drafting captures intent before its shape is settled.

The bumpability guarantee moves to activation. `relay mark active` refuses
to activate a ticket that has no workflow, with an error pointing at either
`--workflow` or `relay ticket` for guided authoring. This closes the same
failure mode — a launched ticket no `relay bump` can ever advance — at the
moment work is approved rather than the moment it is drafted, so a
half-formed draft is never blocked on a workflow decision it isn't ready to
make.

`relay ticket` (guided authoring) fills the workflow in through its
interview skill. `relay recurring` scaffolding (a bare scan-and-launch run
and the on-demand `recurring launch <name>`, including the `relay dream`
alias) and `relay retire` scaffold their own one-shots by calling
`scaffold_task` directly — they are intentional internal exceptions, not
user-authored drafts.

## Two state machines per ticket

- **Control plane (`status`)** — `draft → active → in_progress →
  done`, plus `paused`. Governs *whether* work happens. `relay mark`
  owns the `draft`/`active`/`paused`/`done` transitions; `relay launch`
  owns the one remaining transition, flipping an `active` ticket to
  `in_progress` when it spawns the agent. `bump` ignores `status:`
  entirely (it owns `step:`, not `status:`).
- **Data plane (`step`)** — current position in the frozen workflow.
  Format `N (step-name)`. Owned entirely by `relay bump`. Only moves when
  status is `in_progress`. Bare `relay bump` advances one step; a human
  outside a supervised launch may rewind to an earlier step with `--to` or
  `--backward`. Pausing preserves the step; marking done clears it.

Tickets without a `workflow` field have no steps and move through
statuses directly via `relay mark`. `relay bump` refuses them.

The split is deliberate: each command owns its writes. `relay create`
authors a draft, `relay mark` flips status across the lifecycle,
`relay bump` moves steps, and `relay launch` spawns the agent — flipping
`active → in_progress` as it does. Only `launch` touches both planes, and
only for that single transition.

## Three modes

`mode:` in ticket frontmatter:

- **`interactive`** — human-attended terminal session. Agent gets the
  composed prompt, human stays in the loop. The REPL doesn't terminate on
  its own — `relay bump` / `relay mark done` / `relay panic` signal the
  launch supervisor via the session-scoped `$RELAY_DONE_SENTINEL` file, and
  the supervisor SIGTERMs the REPL. The legacy `DONE_MARKER` PTY byte-match
  exists only as a last-resort fallback if the sentinel file write fails; it
  is not printed on the success path. After teardown, `relay launch` re-reads
  the ticket and either spawns a fresh REPL for the next workflow step (whenever
  it is an *agent's* turn — relaunching the next agent's CLI, so it rotates
  e.g. claude → codex → claude across a peer-review workflow) or returns
  control to the caller (the next step hands off to an owner/human, status
  flipped to `done`/`paused`, or no progress made). The discriminator is
  agent-vs-human, not same-vs-changed assignee. Cross-ticket chaining is
  `relay recurring --interactive`.
- **`auto`** — one-shot autonomous run. Same composed prompt, no
  human input.
- **`script`** — no agent. `relay launch` runs the step's skill
  script directly with secrets injected as env vars.

## Prompt composition

`relay launch` builds one composed prompt and writes it to a temp
file. Layers, in order:

1. Base prompt + mode-specific block (`interactive` / `auto`). Both
   are package resources, not files under `relay-os/`.
2. Global rules (`relay-os/rules.md`).
3. Repo context (`relay-os/context.md` — top-level facts about this
   surface).
4. Ticket contexts (everything in `contexts:` frontmatter list).
5. Task-specific context (the ticket body's inline `## Context`).
6. Ticket-level skills and the current workflow step's skill (if any).
7. The blackboard.
8. The task description (the ticket body's `## Description`).

The agent gets all of this as one input. There is no follow-up
loading.

The composer defuses the session-teardown marker before returning the
assembled prompt. An interactive launch's PTY supervisor tears down the REPL
when the session-scoped `$RELAY_DONE_SENTINEL` file names the launched task.
It still keeps a legacy PTY byte-match fallback for the `DONE_MARKER` byte
sequence, used only if a session-ending command cannot write the sentinel
file. Because any layer above — an injected context, a ticket body — could
quote that literal sequence verbatim, `compose._defuse_done_marker` inserts a
zero-width joiner right after the leading `<<<` so the marker can never appear
intact in composed text. Without that defuse, quoting the marker in a context
or body could SIGTERM the agent mid-session through the fallback watcher.

## Status is the signal

There is no filesystem mutex. The ticket's `status` (`draft`, `active`,
`in_progress`, `paused`, `done`) is the signal that someone is — or
isn't — working on a task. `relay launch` accepts an `active` or
`in_progress` ticket and refuses any other status, pointing the
operator at `relay mark active <slug>` — there is no auto-flip from
draft. The failure mode of two divergent workers (two blackboard edits,
two PR branches) is visible and recoverable in git; the cost of a hard
mutex (stale lock files, `--force` flags, orphan-lock cleanup) is not.

## Command Surface

The command reference lives in `relay/cli`. The important architectural split
is that foreground commands operate on files in the current `relay-os/`; there
is no server-side state behind them.

## Dream's known-skill contract

Dream is not a plugin host. The body of the `relay-os/recurring/dream/ticket.md`
template — composed into each Dream task's `## Description` — owns an explicit,
ordered list of known skills it will run and is the only control point.
Dropping a SKILL.md under `bootstrap/dream/tasks/` does not enable it; there is
no recursive discovery, no registry, and no daemon. Adding another Dream skill
is a normal Relay code/docs change to that list.

Dream-owned scripts are skills attached to Relay tasks; they are never
standalone execution units.

A Dream worker is a plain skill. The shipped Relay workers live under
`src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/tasks/<name>/`
as a `SKILL.md` (standard `name` + `description` frontmatter, plus an
optional `script: <filename>` entry point) alongside that script. `relay
init` materializes them into `relay-os/bootstrap/skills/...`, so a workflow
step references the worker by ref `bootstrap/dream/tasks/<name>`. Running a
worker is just a `mode: script` Relay task whose one workflow step names that
skill — it gets a normal ticket, blackboard, and log. There is no separate
"Dream worker" Python shape, no `worker.main()` import from `relay.commands`,
and no in-process call path; the worker runs end-to-end through the same
launch machinery as any other script step.

A `mode: script` launch injects task and skill metadata as environment
variables instead of CLI argument plumbing — a worker script reads these, not
a `--blackboard` flag. The full set: `RELAY_TASK_SLUG`, `RELAY_TASK_DIR`,
`RELAY_TASK_TICKET`, `RELAY_TASK_BLACKBOARD`, `RELAY_TASK_LOG`,
`RELAY_RELAY_OS_ROOT`, `RELAY_REPO_ROOT`, `RELAY_SKILL_NAME`, and
`RELAY_SKILL_DIR`. `RELAY_RELAY_OS_ROOT` is the `relay-os/` root; `RELAY_REPO_ROOT`
is the host repo (its parent when `relay-os/` is nested in a repo).

Each known skill's `SKILL.md` carries a `## Known Skill Contract` section
with these fields:

- `Purpose` — the maintenance question this skill answers.
- `Runs` — exact command, manual instructions, or script entry point.
- `Inputs` — files, commands, APIs, or task state the skill may read.
- `May change` — exact files/refs/state the skill may edit, or `none`.
- `Action` — one of `report-only`, `proposal-only`, `pr-required`,
  `direct-fix`.
- `Idempotency` — how reruns avoid duplicate work.
- `Stop and ask` — conditions that require human review before continuing.
- `Output` — blackboard section, PR link, created ticket, or no-op.

Each known script skill writes its own `## Dream Skill: <name>` section to its
child task blackboard. The orchestrator appends one `## Dream Run Summary`
that lists each skill's result using a small fixed vocabulary:
`no-op`, `reported`, `proposed`, `direct-fixed`, `pr-opened`,
`human-needed`.

Destructive behavior (deleting task directories, deleting git refs,
changing lifecycle state, touching secrets) is never implicit. A known skill may declare a direct destructive change only when
the rule is deterministic, narrow, and named in `May change`; otherwise it
must use `proposal-only` or `pr-required`. Repos that want a different
maintenance loop define their own task (e.g. `rem` under
`relay-os/recurring/`) with its own dispatch rules — that is user space and
is not plugged into bootstrap Dream.

## What this context does NOT cover

- Where files live in source / how to test (see `relay/codebase`).
- The "why" / philosophy (see `relay/principles`).
- Current iteration's open decisions (see `relay/current-direction`).
- Reusable compositions of these primitives — e.g. the spool, a blackboard
  used as a producer/consumer queue (see `relay/patterns`).
