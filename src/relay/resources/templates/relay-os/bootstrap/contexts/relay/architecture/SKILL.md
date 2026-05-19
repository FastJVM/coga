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
  Local skills override bundled skills with the same ref.
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
  stateless launch targets for skills. No status, no workflow. Used for
  ticket-less re-entry points like `relay launch bootstrap/orient`
  (the `chat` alias). They are never factories — `relay launch` no
  longer scaffolds new tickets from shims; use `relay draft` or `relay ticket`
  for that.
- **Bundled batteries** are package-backed skills, contexts, hooks, and launch
  shims materialized under `relay-os/bootstrap/` by `relay init` and
  `relay init --update`. `pip install relay-os` puts them in the wheel; init
  materializes them into each repo. They are inspectable local files, but
  edits under `bootstrap/` are overwritten on update. Copy a skill or context
  to the matching `relay-os/skills/` or `relay-os/contexts/` ref to override it.
- **Dream** is Relay's generic ticket cleanup pass. A Dream run is an ordinary
  ad-hoc task created by `relay dream`; its body scans the ticket set, runs
  fixed Relay housekeeping skills, proposes cleanup, and writes reviewable
  results to its blackboard.
- **REM** is repo/user-specific recurring maintenance. A REM run is an
  ordinary recurring task whose body defines that repo's operational checks,
  domain skills, output conventions, and review gates.

Contexts and skills both use the SKILL.md format (frontmatter `name`
+ `description`, then body). Zero proprietary extensions — same format
Claude Code and Codex use.

## Two state machines per ticket

- **Control plane (`status`)** — `draft → active → in_progress → done`, plus
  `paused`. `draft` is unapproved, `active` is approved/queued, and
  `in_progress` is launched work. `relay mark active | paused | done` owns
  human-visible status changes; `relay launch` owns the `active` →
  `in_progress` start transition.
- **Data plane (`step`)** — current position in the frozen workflow.
  Format `N (step-name)`. Owned entirely by `relay bump`. Only advances
  when status is `in_progress`. Pausing preserves the step; marking done
  clears it.

Tickets without a `workflow` field have no steps and move through
statuses directly via `relay mark`. `relay bump` refuses them.

The split is deliberate: each command owns a narrow move. `relay draft`
authors a raw draft, `relay ticket` runs guided ticket authoring, `relay mark`
approves/pauses/finishes work, `relay launch` starts or resumes execution, and
`relay bump` advances steps.

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

## Status is the signal

There is no filesystem mutex. The ticket's `status` (`draft`, `active`,
`in_progress`, `paused`, `done`) is the signal that someone is — or isn't —
working on a task. `relay launch` refuses drafts and paused/done tickets,
starts active tickets by marking them `in_progress`, and resumes tickets that
are already `in_progress`. The failure mode of two divergent workers (two
blackboard edits, two PR branches) is visible and recoverable in git; the cost
of a hard mutex (stale lock files, `--force` flags, orphan-lock cleanup) is not.

## Command Surface

The command reference lives in `relay/cli`. The important architectural split
is that foreground commands operate on files in the current `relay-os/`; there
is no server-side state behind them.

## Dream's known-skill contract

Dream is not a plugin host. The body of `bootstrap/dream` (the `dream.md`
prompt resource) owns an explicit, ordered list of known skills it will run
and is the only control point. Dropping a SKILL.md under
`bootstrap/dream/tasks/` does not enable it; there is no recursive discovery,
no registry, and no daemon. Adding another Dream skill is a normal Relay
code/docs change to that list.

Dream-owned scripts are skills attached to Relay tasks; they are never
standalone execution units.

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
