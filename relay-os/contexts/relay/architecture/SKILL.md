---
name: relay/architecture
description: Mental model for relay — primitives, planes, composition. What an agent needs to know to reason about how relay works as a system.
---

# Relay architecture

Relay is a markdown-first, git-backed company OS. Everything an agent
operates on is a file in `relay-os/`. There is no database, no daemon,
no in-memory state.

## Primitives

- **Tickets** live as directories under `relay-os/tasks/`: a task is any
  directory containing a `ticket.md`, at **any depth** — directly
  (`tasks/<slug>/`) or in a sub-directory (`tasks/marketing/social/<slug>/`).
  The sub-directories are just plain directories you organize with
  `mkdir` / `mv` / `rm` (nest them as deep as you like), and a task directory
  is never recursed into. A task is referenced by
  its **path under `tasks/`** — its bare leaf at the top level, otherwise the
  relative path (`marketing/relay-crm`, `marketing/social/relaunch`) — used as
  the qualified slug across CLI commands, `relay status`, and notifications.
  Two sibling directories may therefore reuse a leaf name, and a nested task's
  bare leaf does not resolve on its own. Agents should use the composed
  prompt's exact task directory instead of reconstructing it from the slug.
  Relay reads this tree — `relay status <dir>` filters to a sub-tree — but
  never reimplements it. Each task has
  `ticket.md` (frontmatter + body), `log.md` (append-only, written by CLI
  commands only), and `blackboard.md` (free-form workspace shared between
  human and agent).
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
  scans them, creates the current run at the stable path-qualified task ref
  `tasks/recurring/<name>/` (`recurring/<name>` in CLI/status/notifications),
  records the serviced period as `last_serviced_period` in the template
  blackboard, and launches the due ones. The created tasks then use the same
  ticket, workflow, launch, bump, and blackboard machinery as any other task.
- **Bootstrap shims** in `relay-os/bootstrap/<name>/ticket.md` are
  stateless launch targets for skills. No status, no workflow. Used for
  ticket-less re-entry points like `relay launch bootstrap/orient`
  (the `chat` alias). They are never factories — `relay launch` no
  longer creates new tickets from shims; use `relay create` for that.
- **Bundled batteries** are package-backed core skills, contexts, hooks, and
  launch shims materialized under `relay-os/bootstrap/` by `relay init` and
  `relay init --update`. `pip install relay-os` puts them in the wheel; init
  materializes them into each repo. They are inspectable local files, but
  edits under `bootstrap/` are overwritten on update. Optional domain skills
  declared in Relay's managed-skill manifest install into `relay-os/skills/`
  through the public skill installer instead of being copied from templates;
  install failures for optional skills warn without breaking offline init.
  Copy a skill or context to the matching `relay-os/skills/` or
  `relay-os/contexts/` ref to override it.
- **Dream** is Relay's generic ticket cleanup pass. It is a recurring task
  template (`relay-os/recurring/dream/`) plus a `dream` alias — not a
  built-in command. `relay recurring` creates and launches it when its
  weekly schedule is due; the `relay dream` alias (`recurring launch dream`)
  creates and launches it on demand. The parent task orchestrates child `mode: script`
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

The rule is symmetric, and `relay validate` enforces the other half: a
workflow is mandatory everywhere *except* `draft`. A workflow-less
`active`/`in_progress`/`paused` ticket is a structurally stuck task that no
`relay bump` can advance, so the validator reports it as an **error**
(`active-no-workflow`) — the activation gate and the validator now agree
instead of the validator nagging the one state (`draft`) where workflow-less
is allowed. A workflow-less `done` ticket is finished and immutable, so it is
left alone.

`relay ticket` (guided authoring) fills the workflow in through its
interview skill. `relay recurring` creating (a bare scan-and-launch run
and the on-demand `recurring launch <name>`, including the `relay dream`
alias) and `relay retire` create their own one-shots straight to `active`
by calling `create_task` directly — but they are **not** workflow-less
exceptions: a template that declares no workflow (and every retire task)
creates with the one-step `direct/body` workflow, which runs the ticket
body's ordered phases directly. There is no sanctioned workflow-less active
task; the invariant holds for machine-authored tasks too.

## Two state machines per ticket

- **Control plane (`status`)** — `draft → active → in_progress →
  done`, plus `paused`. Governs *whether* work happens. `relay mark`
  owns the `draft`/`active`/`paused`/`done` transitions; `relay launch`
  flips an `active` ticket to `in_progress` when it spawns the agent, and —
  since launching is itself the readiness signal — also performs the
  `mark active` step inline for a ticket that is still `draft`/`paused`/`done`
  before that flip. `bump` ignores `status:` entirely (it owns `step:`,
  not `status:`).
- **Data plane (`step`)** — current position in the frozen workflow.
  Format `N (step-name)`. Owned entirely by `relay bump`. Only moves when
  status is `in_progress`. Bare `relay bump` advances one step; a human
  outside a supervised launch may rewind to an earlier step with `--to` or
  `--backward`. Pausing preserves the step; marking done clears it.

Tickets without a `workflow` field have no steps and move through
statuses directly via `relay mark`. `relay bump` refuses them.

The split is deliberate: each command owns its writes. `relay create`
authors a draft, `relay mark` flips status across the lifecycle,
`relay bump` moves steps, and `relay launch` spawns the agent — bringing the
ticket to `active` first if it isn't already (reusing `relay mark active`),
then flipping `active → in_progress` as it does. `launch` is the one command
that touches both planes.

## Three modes

`mode:` in ticket frontmatter:

- **`interactive`** — human-attended terminal session. Agent gets the
  composed prompt, human stays in the loop. The REPL doesn't terminate on
  its own — `relay bump` / `relay mark done` / `relay panic` signal the
  launch supervisor via the session-scoped `$RELAY_DONE_SENTINEL` file, and
  the supervisor SIGTERMs the REPL. The sentinel file is the only done
  channel: the supervisor honors it only when the file's content names the
  launched task's session id, so a session-ending command run by an
  unrelated descendant that merely inherited the env var cannot trigger
  teardown. After teardown, `relay launch` re-reads
  the ticket and either spawns a fresh REPL for the next workflow step (whenever
  it is an *agent's* turn — relaunching the next agent's CLI, so it rotates
  e.g. claude → codex → claude across a peer-review workflow) or returns
  control to the caller (the next step hands off to an owner/human, status
  flipped to `done`/`paused`, or no progress made). The discriminator is
  agent-vs-human, not same-vs-changed assignee. Cross-ticket chaining is
  `relay recurring --interactive`.
- **`auto`** — one-shot autonomous run. Same composed prompt, no
  human input. An operator may opt an agent into skipping its CLI's
  per-command permission/approval prompts for these runs with a partial
  `[agents.<name>]` table in `relay.local.toml`: `skip_permissions = "auto"`
  plus `skip_permissions_argv = "..."` (one string, `shlex`-split, inserted
  after the session-name argv and before the auto argv/prompt). The policy
  is machine-local only — either key in shared `relay.toml` fails config
  load — and applies only to normal task tickets in effective `mode: auto`:
  interactive launches, bootstrap/discussion shims, and script tasks keep
  today's behavior. Supervised chains re-resolve it per step for whichever
  agent the step rotated to, and `"auto"` with no configured argv fails the
  launch loud before spawning.
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

Note what is deliberately **absent**: no `log.md` is ever a composition
layer — not the task's, not a recurring template's. `log.md` is append-only
audit history and never enters an agent's context, so it can grow without
bound. Only `blackboard.md` (layer 7) carries state forward into the prompt.
The consequence is a hard division of labor: working state that the next run
must read goes in the blackboard (and is therefore composed, so keep it
small); durable history goes in the log (never composed, so let it
accumulate).

An interactive launch's PTY supervisor tears down the REPL when the
session-scoped `$RELAY_DONE_SENTINEL` file names the launched task — its sole
done channel. Because the signal is a side-channel file whose content must
match the launched task's session id, there is nothing in the composed prompt
or PTY byte stream to trip: an agent that reads, greps, or quotes a teardown
string at runtime cannot end its own (or a parent's) session, so the composer
returns the assembled prompt verbatim with no defusal step.

## Status is the signal

There is no filesystem mutex. The ticket's `status` (`draft`, `active`,
`in_progress`, `paused`, `done`) is the signal that someone is — or
isn't — working on a task. `relay launch` accepts an `active` or
`in_progress` ticket directly, and treats a launch of any other status as
the readiness decision itself: a `draft` / `paused` / `done` ticket is run
through `relay mark active` inline before the agent starts (re-activating a
`done` ticket restarts its workflow at step 1). A workflow-less or
required-extension-incomplete ticket still can't be activated, so those
launches fail loud with the same remedy `mark active` gives. The failure
mode of two divergent workers (two blackboard edits,
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

Dream's decide-half subagent scans (the knowledge scan and the contract
audit) are skills too, but **prompt-only**: they live under
`bootstrap/skills/bootstrap/dream/scan/<name>/` (referenced as
`bootstrap/dream/scan/<name>`), a sibling segment to the script workers'
`tasks/`. A prompt-only scan skill carries just `name` + `description`
frontmatter and the classification contract as its body — no `script:` entry
point and no `## Known Skill Contract` block; that shape belongs to the
script workers and is the wrong archetype to copy for a subagent scan. The
Dream template body delegates each scan phase to a subagent running the
skill and keeps only the delegation framing plus the `## Findings` write
target inline. Known limitation: the contract audit's own corpus globs
(`relay-os/contexts/**`, `relay-os/skills/**`) do not cover
`relay-os/bootstrap/skills/**`, so the bundled Dream skills — the scan
skills included — sit outside the surface that audit reads.

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
