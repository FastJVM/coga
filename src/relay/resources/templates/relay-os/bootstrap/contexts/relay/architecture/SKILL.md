---
name: relay/architecture
description: Mental model for relay — primitives, planes, composition, locking. What an agent needs to know to reason about how relay works as a system.
---

# Relay architecture

Relay is a markdown-first, git-backed company OS. Everything an agent
operates on is a file in `relay-os/`. There is no database, no daemon,
no in-memory state.

## Primitives

- **Tickets** live in `relay-os/tasks/<slug>/` as a directory. Each has
  `ticket.md` (frontmatter + body), `log.md` (append-only, written by
  CLI commands only), `blackboard.md` (free-form workspace shared
  between human and agent), and `task.lock` (filesystem mutex).
- **Contexts** are domain knowledge — what's true about the world.
  Live in `relay-os/contexts/`. Attached to tickets via `contexts:`
  frontmatter list.
- **Skills** are process knowledge — how to do a thing. Live in
  `relay-os/skills/`. Attached to **workflow steps**, not tickets.
- **Workflows** are ordered step definitions. Live in
  `relay-os/workflows/`. Frozen into a ticket's frontmatter at
  creation — in-flight tickets are unaffected by later workflow edits.
  Each step may declare an `assignee:` role token (`owner` | `human` |
  `agent`); on bump, the token resolves against the ticket's
  matching role field and rewrites `assignee:`. Steps without one
  leave the assignee unchanged.
- **Recurring templates** live in `relay-os/recurring/`. They scaffold
  ordinary tasks on a schedule via `relay recurring check`; the created tasks
  then use the same ticket, workflow, launch, bump, and blackboard machinery as
  any other task.
- **Bootstrap shims** in `relay-os/bootstrap/<name>/ticket.md` are
  stateless launch targets for skills. No status, no workflow, no
  lock. `relay launch bootstrap/ticket "title"` is the factory
  shorthand to scaffold a new draft + run the bootstrap skill on it.
- **Dream** is Relay's generic ticket cleanup pass. A Dream run is an ordinary
  ad-hoc task created by `relay dream`. The command is the orchestrator: it
  scaffolds the parent task, launches deterministic workers as child
  `mode: script` tasks, copies their results into the parent blackboard, then
  launches the agent for judgment-heavy cleanup. The task body owns the
  ordered pass and run summary.
- **REM** is repo/user-specific recurring maintenance. A REM run is an
  ordinary recurring task whose body defines that repo's operational checks,
  domain skills, output conventions, and review gates.

Contexts and skills both use the SKILL.md format (frontmatter `name`
+ `description`, then body). Zero proprietary extensions — same format
Claude Code and Codex use.

## Two state machines per ticket

- **Control plane (`status`)** — `draft → active → done`, plus
  `paused`. Governs *whether* work happens. Transitions are not
  enforced by code; convention is the authority.
- **Data plane (`step`)** — current position in the frozen workflow.
  Format `N (step-name)`. Only advances when status is `active`.
  Pausing freezes step. Sending back to draft preserves step.

Tickets without a `workflow` field have no steps and move through
statuses directly.

## Three modes

`mode:` in ticket frontmatter:

- **`interactive`** — human-attended terminal session. Agent gets the
  composed prompt, human stays in the loop.
- **`auto`** — one-shot autonomous run. Same composed prompt, no
  human input.
- **`script`** — no agent. `relay launch` runs the step's skill
  script directly with secrets injected as env vars.

## Prompt composition

`relay launch` builds one composed prompt and writes it to a temp
file. Layers, in order:

1. Global rules (from `relay-os/prompt.md` + mode-specific block).
2. Repo context (top-level facts about this surface).
3. Ticket contexts (everything in `contexts:` frontmatter list).
4. Current workflow step's skill (if any).
5. The blackboard.
6. The ticket body itself.

The agent gets all of this as one input. There is no follow-up
loading.

## Locking

`task.lock` is a file-existence lock, local-only, one per task
directory. Under one-task-one-worker (deliberate v1 constraint for
small teams) it's enough. No distributed locking. Stale locks are
reported by Dream's validate-drift worker; deletion still requires human
confirmation that no live worker owns the task.

## Command Surface

The command reference lives in `relay/cli`. The important architectural split
is that foreground commands operate on files in the current `relay-os/`; there
is no server-side state behind them.

## Dream's known-skill contract

Dream is not a plugin host. The body of `bootstrap/dream` (the `dream.md`
prompt resource) owns an explicit, ordered list of known skills and runners,
and is the only control point. Deterministic scripts are launcher-owned child
Relay tasks, so they still get task composition, blackboards, logs, locks, and
recovery; judgment-heavy work is agent-owned. Dropping a SKILL.md under
`bootstrap/dream/tasks/` does not enable it; there is no recursive discovery,
no registry, and no daemon. Adding another Dream skill is a normal Relay
code/docs change to that list.

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

Each known skill writes its own `## Dream Worker: <name>` section to the
Dream run blackboard. The orchestrator appends one `## Dream Run Summary`
that lists each skill's result using a small fixed vocabulary:
`no-op`, `reported`, `proposed`, `direct-fixed`, `pr-opened`,
`human-needed`.

Destructive behavior (deleting task directories, deleting git refs,
removing locks, changing lifecycle state, touching secrets) is never
implicit. A known skill may declare a direct destructive change only when
the rule is deterministic, narrow, and named in `May change`; otherwise it
must use `proposal-only` or `pr-required`. Repos that want a different
maintenance loop define their own task (e.g. `rem` under
`relay-os/recurring/`) with its own dispatch rules — that is user space and
is not plugged into bootstrap Dream.

## What this context does NOT cover

- Where files live in source / how to test (see `relay/codebase`).
- The "why" / philosophy (see `relay/principles`).
- Current iteration's open decisions (see `relay/current-direction`).
