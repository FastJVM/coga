---
name: coga/architecture
description: Mental model for coga — primitives, planes, composition. What an agent needs to know to reason about how coga works as a system.
---

# Coga architecture

Coga is a markdown-first, git-backed company OS. Everything an agent
operates on is a file in `coga-os/`. There is no database, no daemon,
no in-memory state.

## Primitives

- **Tickets** live as directories under `coga-os/tasks/`: a task is any
  directory containing a `ticket.md`, at **any depth** — directly
  (`tasks/<slug>/`) or in a sub-directory (`tasks/marketing/social/<slug>/`).
  The sub-directories are just plain directories you organize with
  `mkdir` / `mv` / `rm` (nest them as deep as you like), and a task directory
  is never recursed into. A task is referenced by
  its **path under `tasks/`** — its bare leaf at the top level, otherwise the
  relative path (`marketing/coga-crm`, `marketing/social/relaunch`) — used as
  the qualified slug across CLI commands, `coga status`, and notifications.
  Two sibling directories may therefore reuse a leaf name, and a nested task's
  bare leaf does not resolve on its own. Agents should use the composed
  prompt's exact task directory instead of reconstructing it from the slug.
  Coga reads this tree — `coga status <dir>` filters to a sub-tree — but
  never reimplements it. A task is a **single file or a directory**, whichever
  it needs: a self-contained task is a bare `tasks/<slug>.md`; a task that needs
  companions (a deferred `script:` file, attachments) is a `tasks/<slug>/`
  directory holding `ticket.md` plus the siblings. (`<slug>.md` and `<slug>/`
  must not both exist; promotion is `mkdir <slug>/ && mv <slug>.md
  <slug>/ticket.md`.) Either way the ticket is YAML frontmatter + body, then a
  fence line `<!-- coga:blackboard -->` followed by the free-form blackboard
  region (the workspace shared between human and agent). The append-only audit
  trail is not in the task file — it lives in one repo-global `coga-os/log.md`
  (written by CLI commands only), each line tagged with its task ref.
- **Contexts** are domain knowledge — what's true about the world.
  Project-local contexts live in `coga-os/contexts/`; bundled Coga
  batteries live in `coga-os/bootstrap/contexts/`. Attached to tickets via
  `contexts:` frontmatter list. Local contexts override bundled contexts with
  the same ref.
- **Skills** are process knowledge — how to do a thing. Project-local skills
  live in `coga-os/skills/`; bundled Coga batteries live in
  `coga-os/bootstrap/skills/`. Attached to **workflow steps**, not tickets.
  Local skills override bundled skills with the same ref. The `skills:`
  ticket-level frontmatter field exists for skill refs that apply to the
  ticket as a whole; `bootstrap/ticket` is the authoring interview and must
  never appear there — `coga ticket` injects it into the launch prompt
  only, never persists it on the ticket.
- **Workflows** are ordered step definitions. A repo's own workflows live in
  `coga-os/workflows/`; package-backed reusable workflows (the core `code/*`
  loop, `dev/with-self-review`, `docs/create-google-doc`, the Dream child
  workflows, `digest/post`) live under `coga-os/bootstrap/workflows/`.
  Resolution is local-first, exactly like skills and contexts: a local
  `workflows/<ref>.md` overrides a bundled `bootstrap/workflows/<ref>.md`.
  Frozen into a ticket's frontmatter at
  creation — in-flight tickets are unaffected by later workflow edits.
  Each step may declare an `assignee:` role token (`owner` | `human` |
  `agent` | `other-agent`); on bump, the token resolves against the ticket's
  matching role field and rewrites `assignee:`. `other-agent` resolves to the
  peer agent (it needs two configured `[agents.*]`) and drives peer-review
  flips (e.g. `code/with-review`) and agent-rotation relaunches. Steps without
  one leave the assignee unchanged.
- **Recurring templates** live in `coga-os/recurring/`. `coga recurring`
  scans them, creates the current run at the stable path-qualified task ref
  `tasks/recurring/<name>/` (`recurring/<name>` in CLI/status/notifications),
  records the serviced period as `last_serviced_period` in the template
  blackboard, and launches the due ones. The created tasks then use the same
  ticket, workflow, launch, bump, and blackboard machinery as any other task.
- **Bootstrap tickets** in `coga-os/bootstrap/<name>/ticket.md` are
  stateless launch targets for skills. No status, no workflow. Used for
  ticket-less re-entry points like `coga launch bootstrap/orient`
  (the `chat` alias). They are never factories — `coga launch` no
  longer creates new tickets from them; use `coga create` for that.
- **Bundled batteries** are package-backed core skills, contexts, reusable
  workflows, hooks, and launch targets materialized under `coga-os/bootstrap/`
  by `coga init` and `coga init --update`. `pip install coga-os` puts them in the wheel; init
  materializes them into each repo. They are inspectable local files, but
  edits under `bootstrap/` are overwritten on update. Optional domain skills
  declared in Coga's managed-skill manifest install into `coga-os/skills/`
  through the public skill installer instead of being copied from templates;
  install failures for optional skills warn without breaking offline init.
  Copy a skill or context to the matching `coga-os/skills/` or
  `coga-os/contexts/` ref to override it.
- **Dream** is Coga's generic ticket cleanup pass. It is a recurring task
  template (`coga-os/recurring/dream/`) plus a `dream` alias — not a
  built-in command. `coga recurring` creates and launches it when its
  weekly schedule is due; the `coga dream` alias (`recurring launch dream`)
  creates and launches it on demand. The parent task orchestrates child script
  tasks over worker skills; its body scans the ticket set, runs fixed Coga
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

`slug`, `title`, `status`, `autonomy`, `owner`, `human`, `agent`,
`assignee`, `watchers`, `workflow`, `step`, `contexts`, `skills`, `secrets`,
`script`.

`slug` is the task's path-qualified reference, recorded on the ticket for
legibility (the path under `tasks/` stays the addressing source of truth).

`secrets` is nullable and declared **inline** — there is no central
`[secrets]` catalog. Absent / `null` / `[]` inject nothing; otherwise it is a
list of single-key maps `- NAME: <ref>` where `<ref>` is an
`op://vault/item/field` 1Password reference (resolved live with `op read`) or
an `env:VAR` indirection (read from the operator's environment). At launch each
ref is resolved and injected as env var `NAME`; the source `env:VAR` is
scrubbed so the child sees only the scoped name. A bare-string entry (the
removed catalog-key form) or a raw literal value is rejected — a literal secret
may not live in a git-committed ticket.

A repo may declare additional fields under `[ticket.fields.<name>]` in
`coga.toml` — see "Ticket frontmatter extensions" below.

## Ticket frontmatter extensions

Per-repo frontmatter fields are declared in `coga.toml`:

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

- `coga create` / `coga ticket` write every declared field into the new
  ticket below the `# --- extensions ---` marker, seeded with the
  declared default (or `""`).
- `coga validate` enforces the schema — declared-but-missing fails
  loud; an enum violation fails loud; an undeclared key not in the
  canonical set is treated as an orphan (warn-only) so removing an
  extension is symmetric.
- `coga mark active` refuses to activate a ticket whose `required`
  fields are empty.

Extensions live in the same frontmatter the prompt composer already
reads, so no extra layer is needed — the field is in every composed
prompt by virtue of being on the ticket.

## Workflow gated at activation, not draft time

`coga create` takes an
*optional* `--workflow <name>`. A workflow-less draft is a valid authoring
state — drafting captures intent before its shape is settled.

The bumpability guarantee moves to activation. `coga mark active` refuses
to activate a ticket that has no workflow, with an error pointing at either
`--workflow` or `coga ticket` for guided authoring. This closes the same
failure mode — a launched ticket no `coga bump` can ever advance — at the
moment work is approved rather than the moment it is drafted, so a
half-formed draft is never blocked on a workflow decision it isn't ready to
make.

The rule is symmetric, and `coga validate` enforces the other half: a
workflow is mandatory everywhere *except* `draft`. A workflow-less
`active`/`in_progress`/`paused` ticket is a structurally stuck task that no
`coga bump` can advance, so the validator reports it as an **error**
(`active-no-workflow`) — the activation gate and the validator now agree
instead of the validator nagging the one state (`draft`) where workflow-less
is allowed. A workflow-less `done` ticket is finished and immutable, so it is
left alone.

`coga ticket` (guided authoring) fills the workflow in through its
interview skill. `coga recurring` creating (a bare scan-and-launch run
and the on-demand `recurring launch <name>`, including the `coga dream`
alias) and `coga retire` create their own one-shots straight to `active`
by calling `create_task` directly — but they are **not** workflow-less
exceptions: a template that declares no workflow (and every retire task)
creates with the one-step `direct/body` workflow, which runs the ticket
body's ordered phases directly. There is no sanctioned workflow-less active
task; the invariant holds for machine-authored tasks too.

## Two state machines per ticket

- **Control plane (`status`)** — `draft → active → in_progress →
  done`, plus `paused`. Governs *whether* work happens. `coga mark`
  owns the `draft`/`active`/`paused`/`done` transitions; `coga launch`
  flips an `active` ticket to `in_progress` when it spawns the agent, and —
  since launching is itself the readiness signal — also performs the
  `mark active` step inline for a ticket that is still `draft` or `paused`
  before that flip. A `done` ticket is finished: launch refuses it and leaves
  it untouched rather than restarting its workflow. `bump` ignores `status:`
  entirely (it owns `step:`, not `status:`).
- **Data plane (`step`)** — current position in the frozen workflow.
  Format `N (step-name)`. Owned entirely by `coga bump`. Only moves when
  status is `in_progress`. Bare `coga bump` advances one step; a human
  outside a supervised launch may rewind to an earlier step with `--to` or
  `--backward`. Pausing preserves the step; marking done clears it.

Tickets without a `workflow` field have no steps and move through
statuses directly via `coga mark`. `coga bump` refuses them.

The split is deliberate: each command owns its writes. `coga create`
authors a draft, `coga mark` flips status across the lifecycle,
`coga bump` moves steps, and `coga launch` spawns the agent — bringing a
`draft` or `paused` ticket to `active` first (reusing `coga mark active`),
then flipping `active → in_progress` as it does. `launch` is the one command
that touches both planes.

## Autonomy and execution

A task does **not** declare what *kind* of work it is — that is deduced from
its content and its workflow steps. The single declared execution axis is
`autonomy:` (it replaced the former `mode:`); whether a given step runs a
script or composes an agent is deduced, not declared.

`autonomy:` in ticket frontmatter:

- **`interactive`** — human-attended terminal session. Agent gets the
  composed prompt, human stays in the loop. The REPL doesn't terminate on
  its own — `coga bump` / `coga mark done` / `coga panic` signal the
  launch supervisor via the session-scoped `$COGA_DONE_SENTINEL` file, and
  the supervisor SIGTERMs the REPL. The sentinel file is the only done
  channel: the supervisor honors it only when the file's content names the
  launched task's session id, so a session-ending command run by an
  unrelated descendant that merely inherited the env var cannot trigger
  teardown. After teardown, `coga launch` re-reads
  the ticket and either spawns a fresh REPL for the next workflow step (whenever
  it is an *agent's* turn — relaunching the next agent's CLI, so it rotates
  e.g. claude → codex → claude across a peer-review workflow) or returns
  control to the caller (the next step hands off to an owner/human, the status
  flipped to `done`/`paused`, the agent panicked or exited non-zero, or no
  progress was made). The discriminator is agent-vs-human, not
  same-vs-changed assignee. Each respawn gives the next step a clean prompt
  scope, with no carryover reasoning from the previous skill. Cross-ticket
  chaining is `coga recurring --interactive`.
- **`auto`** — one-shot autonomous run. Same composed prompt, no
  human input. **Note: `autonomy: auto` launches are currently temporarily
  disabled** — `coga launch` refuses them
  (`src/coga/commands/launch.py`) and recurring enforces the same freeze
  (`src/coga/recurring.py`); the description below documents the intended
  design for when it is re-enabled. An operator may opt an agent into skipping its CLI's
  per-command permission/approval prompts for these runs with a partial
  `[agents.<name>]` table in `coga.local.toml`: `skip_permissions = "auto"`
  plus `skip_permissions_argv = "..."` (one string, `shlex`-split, inserted
  after the session-name argv and before the auto argv/prompt). The policy
  is machine-local only — either key in shared `coga.toml` fails config
  load — and applies only to normal task tickets in effective `autonomy: auto`:
  interactive launches, bootstrap/discussion tickets, and script steps keep
  today's behavior. (`auto` is currently frozen, as `mode: auto` was.) Supervised chains re-resolve it per step for whichever
  agent the step rotated to, and `"auto"` with no configured argv fails the
  launch loud before spawning.
Script vs. agent is **deduced**, not declared — there is no `mode: script`. A
workflow step runs a script when it resolves to a script entry: its single
skill's `script:`, or (for a no-skill step, or a workflow-less task) the
ticket's own `script:` field. Otherwise the step composes a prompt and spawns
the step's agent. A "mixed" task is just a workflow with both kinds of steps
over one ticket. A ticket's `script:` is either `inline` (a fenced code block
under the body's `## Script` heading) or a sibling filename (which makes the
task take its directory form). Script steps inject secrets as env vars and run
with no agent; `autonomy` does not apply to them.

## Prompt composition

`coga launch` builds one composed prompt and writes it to a temp
file. Layers, in order:

1. Base prompt + mode-specific block (`interactive` / `auto`). Both
   are package resources, not files under `coga-os/`.
2. Repo context (`coga-os/context.md` — top-level facts about this
   surface).
3. Ticket contexts (everything in `contexts:` frontmatter list).
4. Task-specific context (the ticket body's inline `## Context`).
5. Ticket-level skills and the current workflow step's skill (if any).
6. The blackboard.
7. The task description (the ticket body's `## Description`).

The agent gets all of this as one input. There is no follow-up
loading.

Note what is deliberately **absent**: the `coga-os/log.md` audit log is never
a composition layer. It is the one repo-global, append-only file, lives outside
every task directory, and never enters an agent's context, so it can grow
without bound. Only the blackboard region (layer 7) carries state forward into
the prompt.
The consequence is a hard division of labor: working state that the next run
must read goes in the blackboard (and is therefore composed, so keep it
small); durable history goes in the log (never composed, so let it
accumulate).

An interactive launch's PTY supervisor tears down the REPL when the
session-scoped `$COGA_DONE_SENTINEL` file names the launched task — its sole
done channel. Because the signal is a side-channel file whose content must
match the launched task's session id, there is nothing in the composed prompt
or PTY byte stream to trip: an agent that reads, greps, or quotes a teardown
string at runtime cannot end its own (or a parent's) session, so the composer
returns the assembled prompt verbatim with no defusal step.

## Status is the signal

There is no filesystem mutex. The ticket's `status` (`draft`, `active`,
`in_progress`, `paused`, `done`) is the signal that someone is — or
isn't — working on a task. `coga launch` accepts an `active` or
`in_progress` ticket directly, and treats a launch of `draft` or `paused` as
the readiness decision itself: the ticket is run through `coga mark active`
inline before the agent starts. A `done` ticket is refused and left untouched;
launching a finished ticket must not restart its workflow. A workflow-less or
required-extension-incomplete ticket still can't be activated, so those
launches fail loud with the same remedy `mark active` gives. The failure mode
of two divergent workers (two blackboard edits, two PR branches) is visible
and recoverable in git; the cost of a hard mutex (stale lock files, `--force`
flags, orphan-lock cleanup) is not.

## Identity and capability boundaries

"Who is acting?" and "what may this action use?" resolve to four boundaries.
Coga stays classical: local files and standard CLIs first, a hosted crossing
only where a v1 requirement genuinely needs one, no secret or account state
committed to git.

- **Local user / operator.** Coga does **not** own the human's identity. The
  operator is the OS user plus the local tools they already authenticate: `git`,
  `ssh-agent` / git credential helpers, and `gh`. Coga inspects these and fails
  with actionable setup hints (`gh auth login`, fix your git remote); it never
  stores a GitHub PAT or reimplements GitHub auth for normal human PR work. Git
  transport uses the user's configured remote; GitHub PR/API operations use
  `gh` auth.
- **Repo / install identity.** The repo is identified by the git checkout and
  `coga-os/` config. An install may additionally carry an anonymous telemetry
  identity, generated locally and stored only in gitignored local config/state —
  it counts active installs, it never names a person, repo, or path.
- **Skill / task capability.** A task's capabilities are its ticket-level
  `secrets:` list, declared **inline** — each entry is a single-key map
  `NAME: <ref>` whose `<ref>` is an `env:VAR` or `op://vault/item/field`
  indirection (both safe to commit — they are pointers, not values; a raw
  literal is rejected). There is no central `[secrets]` catalog: the ticket
  carries the reference directly, and the trust boundary on what an `op://`
  reference can read is 1Password's own vault/service-account permissions, not
  a Coga allow-list. Launch resolves each ref live and fails loud when it
  cannot be satisfied (`op` missing / not signed in / `op read` non-zero, or an
  unset `env:VAR`) — error messages name the Coga secret name and reference,
  never the value. The extension seam for new reference providers is **prefix
  dispatch in `config.py`** (`parse_inline_secrets` / `select_launch_secrets`),
  not a provider registry: a future provider is another explicit branch on the
  same shared secret path.
- **Hosted endpoint.** v1 has at most one hosted crossing — the anonymous
  telemetry sink, with a trivial opt-out. Coga does **not** ship a hosted
  account, signup/login flow, API-token store, or sync backend in v1.

## Command Surface

The command reference lives in `coga/cli`. The important architectural split
is that foreground commands operate on files in the current `coga-os/`; there
is no server-side state behind them.

## Dream's known-skill contract

Dream is not a plugin host. The body of the `coga-os/recurring/dream/ticket.md`
template — composed into each Dream task's `## Description` — owns an explicit,
ordered list of known skills it will run and is the only control point.
Dropping a SKILL.md under `bootstrap/dream/tasks/` does not enable it; there is
no recursive discovery, no registry, and no daemon. Adding another Dream skill
is a normal Coga code/docs change to that list.

Dream-owned scripts are skills attached to Coga tasks; they are never
standalone execution units.

A Dream worker is a plain skill. The shipped Coga workers live under
`src/coga/resources/templates/coga-os/bootstrap/skills/bootstrap/dream/tasks/<name>/`
as a `SKILL.md` (standard `name` + `description` frontmatter, plus an
optional `script: <filename>` entry point) alongside that script. `coga
init` materializes them into `coga-os/bootstrap/skills/...`, so a workflow
step references the worker by ref `bootstrap/dream/tasks/<name>`. Running a
worker is just a script-step Coga task whose one workflow step names that
skill — it gets a normal ticket, blackboard, and log. There is no separate
"Dream worker" Python shape, no `worker.main()` import from `coga.commands`,
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
(`coga-os/contexts/**`, `coga-os/skills/**`) do not cover
`coga-os/bootstrap/skills/**`, so the bundled Dream skills — the scan
skills included — sit outside the surface that audit reads.

A script-step launch injects task and skill metadata as environment
variables instead of CLI argument plumbing — a worker script reads these, not
a `--blackboard` flag. The full set: `COGA_TASK_SLUG`, `COGA_TASK_DIR`,
`COGA_TASK_TICKET`, `COGA_TASK_BLACKBOARD`, `COGA_TASK_LOG`,
`COGA_COGA_OS_ROOT`, `COGA_REPO_ROOT`, `COGA_SKILL_NAME`, and
`COGA_SKILL_DIR`. `COGA_COGA_OS_ROOT` is the `coga-os/` root; `COGA_REPO_ROOT`
is the host repo (its parent when `coga-os/` is nested in a repo).

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
`coga-os/recurring/`) with its own dispatch rules — that is user space and
is not plugged into bootstrap Dream.

## What this context does NOT cover

- Where files live in source / how to test (see `coga/codebase`).
- The "why" / philosophy (see `coga/principles`).
- Current iteration's open decisions (see `coga/current-direction`).
- Reusable compositions of these primitives — e.g. the spool, a blackboard
  used as a producer/consumer queue (see `coga/patterns`).
