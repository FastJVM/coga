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
- **Bootstrap shims** in `relay-os/bootstrap/<name>/ticket.md` are
  stateless launch targets for skills. No status, no workflow, no
  lock. `relay launch bootstrap/ticket "title"` is the factory
  shorthand to scaffold a new draft + run the bootstrap skill on it.

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
cleaned by the dream/drift validation script.

## Six commands

`relay create`, `relay launch`, `relay status`, `relay bump`,
`relay panic`, `relay slack`. That's the whole CLI. Everything else
is a flag or a subcommand on these.

## What this context does NOT cover

- Where files live in source / how to test (see `relay/codebase`).
- The "why" / philosophy (see `relay/principles`).
- Current iteration's open decisions (see `relay/current-direction`).
