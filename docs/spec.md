# Relay CLI — spec (consolidated)

This document merges `relay-spec-v2` and all updates from `relay-spec-updates` into a single source of truth.

---

## `relay.toml`

```toml
version = 1

# --- Projects ---

[projects.email-tool]
type = "repo"
remote = "git@github.com:company/email-tool.git"
default_status = "ready"

[projects.site]
type = "repo"
remote = "git@github.com:company/site.git"
default_status = "ready"

[projects.frontend]
type = "repo"
remote = "git@github.com:company/frontend.git"
default_status = "ready"

[projects.content]
type = "local"
default_status = "ready"

[projects.ops]
type = "local"
default_status = "design"

# --- Agents ---

[agents.claude]
cli = "claude"
interactive = "--append-system-prompt-file"
auto = "-p"
file = "CLAUDE.md"
mode = "local"

[agents.codex]
cli = "codex"
interactive = "exec"
auto = "exec"
file = "AGENTS.md"
mode = "local"

[agents.opencode]
cli = "opencode"
interactive = "run"
auto = "run"
file = "AGENTS.md"
mode = "local"

# --- Assignees ---
# nickname → agent type. Nicknames are per-person, not global.
# Multiple people can use the same nickname (e.g. both have "claude2").

[assignees.marc]
agents = {"claude1": "claude", "claude2": "claude", "my IDE": "cursor"}
slack = "U04ABCDEF"

[assignees.pierre]
agents = {"claude2": "claude", "goat": "copilot"}
slack = "U04GHIJKL"

# --- Slack ---

[slack]
webhook = "https://hooks.slack.com/services/xxx"
```

### Agent config fields

| Field | Description |
|---|---|
| `cli` | Binary name. |
| `interactive` | Flag/subcommand for human-attended sessions. Agent starts with composed context loaded; human is present in terminal. For Claude Code: `--append-system-prompt-file` loads the composed context as system-level instructions while keeping an interactive session open. |
| `auto` | Flag/subcommand for autonomous execution. Agent receives composed context as a one-shot prompt, runs to completion without human input. For Claude Code: `-p` sends the prompt and exits when done. |
| `file` | Instruction file (CLAUDE.md, AGENTS.md, etc.). Developer-owned — Relay does **not** overwrite it. Fallback for agents that don't support CLI prompt injection. |
| `mode` | `local` for now. Future: `remote`, `cloud`. |

### `relay.local.toml` (gitignored, per machine)

```toml
user = "marc"

[paths]
email-tool = "~/projects/email-tool"
site = "~/projects/site"
frontend = "~/projects/frontend"
content = "~/projects/content"
ops = "~/projects/ops"

[secrets]
linkedin_token = "env:LINKEDIN_TOKEN"
linkedin_person_id = "env:LINKEDIN_PERSON_ID"
stripe_key = "env:STRIPE_SECRET_KEY"
reddit_client_id = "env:REDDIT_CLIENT_ID"
reddit_client_secret = "env:REDDIT_CLIENT_SECRET"
github_token = "env:GITHUB_TOKEN"
```

Shared config has the what, local config has the where and the credentials.

---

## Repo structure

Relay is a company OS — one repo containing everything the company runs on: code workflows, content ops, research processes, finance tasks, agent skills. Everyone on the team has full read access. No ACLs, no siloing. This is an explicit architectural decision for small, high-trust teams: the overhead of access control costs more than it protects. Credentials never live in the repo (see `relay.local.toml`).

Skills, workflows, and recurring templates all support arbitrary depth nesting. There is no fixed two-level `<domain>/<skill>` constraint — paths reflect the actual structure of your company's knowledge.

```
relay-os/
  relay.toml
  relay.local.toml          ← gitignored
  rules.md                  ← global rules, inlined in every task
  skills/
    content/
      brand-voice/SKILL.md
      product-changelog/SKILL.md
      linkedin/SKILL.md, post.py
      reddit/SKILL.md, read-thread.py, reply.py
    infra/
      deployment/SKILL.md
      auth/SKILL.md
      testing-conventions/SKILL.md
    email/
      stripe-check/SKILL.md, check-failures.py
    meta/
      dream/SKILL.md
      create-suggest/SKILL.md
  contexts/
    email/
      deliverability/
        dns/SKILL.md
        SKILL.md
      payment-flow/SKILL.md
      stripe/SKILL.md
    ops/
      customer-tiers/SKILL.md
  workflows/
    code/
      autonomous.md
      with-review.md
    content/
      post.md
      newsletter.md
    admin/
      accounting-reconciliation.md
    ops.md
  recurring/
    weekly-deliverability-check.md
    stripe-failed-payments.md
    monthly-newsletter.md
    post-deploy-health.md
  scripts/
    cron.sh                  ← entry point for system cron
```

> **Future consideration:** contractor access and per-domain ACLs are not designed for now. If the team grows to include external contributors or lower-trust roles, a submodule-per-domain strategy is the likely path — one architectural seam rather than a full permission system.

> **Git as sync layer.** Git is the v1 sync mechanism — zero infrastructure, free versioning, works with existing developer workflows. This is a deliberate choice for small teams (2-5 people), not a permanent architectural commitment. At 10+ people or with real-time coordination needs, git push/pull becomes a bottleneck and merge conflicts on task files become frequent. A server-backed sync layer is the likely v2/v3 path. For now, conflicts are rare (see one-task-one-worker constraint) and manually resolved when they occur.

### Project directory structure

```
~/projects/email-tool/
  relay-os/
    context.md              ← project base context
    counter                 ← next task ID (plain integer, auto-incremented by relay create)
    tasks/
      003-fix-retry-logic/
        ticket.md           ← assignee, status, workflow step, description, context
        log.md              ← append-only, written by CLI commands only
        blackboard.md       ← shared workspace (see below)
        task.lock            ← serializes concurrent access
  CLAUDE.md                 ← developer-owned, NOT overwritten by relay
  [project files...]
```

---

## Goals / Insights

- Small team 5-10 people
- Work for everything (not just code but marketing, etc.). CompanyOS — a repo of all tasks/processes
- The key problem for agents is knowledge management (understand what to know)
- It's easier to have a human manage KM — too important to leave to AI for recurring tasks and important ones
- Once you have figured out KM, then it's context loading
- Then it's task assignment + memory (for in between runs) and you want to move a task from an AI to a human and vice versa. Ticket is a good abstraction for that — it enriches the context
- Agents have an owner — they're bound to a person, not to a project. A person can have multiple instances of the same agent type (e.g. two Claude Code sessions). Nicknames distinguish them. Dispatch key is always (user, nickname)

---

## Decided — key concepts

These are locked in. Not yet built, but the design is final.

**Projects are locations.** Type (repo/local), remote URL, local path, default status. No skills or workflow config — those are per-task.

**Agents are types.** An agent type defines cli binary, instruction file, and mode. `[agents.claude]` is the template — it says "Claude Code uses `claude` cli, reads `CLAUDE.md`, runs locally." Agent types are not tied to a person or project.

**Agent instances have an owner.** Each person owns named instances of agent types. Marc has "claude1" (type: claude), "claude2" (type: claude), "my IDE" (type: cursor). Pierre has "claude2" (type: claude), "goat" (type: copilot). Nicknames are per-person — no global collision. The dispatch key is always `(user, nickname)`. `relay launch claude1` resolves the current user from `relay.local.toml`, finds their "claude1", and uses the `claude` agent type config.

**Assignees are humans.** Humans own agent instances and are the `owner` of tasks. The `assignee` field on a ticket is who's currently doing the work — a human name or an agent nickname. Reassignment is a deliberate action, not an automatic flip. The ticket is the source of truth for who's assigned.

---

### Skills

Skills are knowledge. They follow the `SKILL.md` standard — the same format used by Claude Code and OpenAI Codex. A relay skill IS a Claude Code skill IS a Codex skill. Zero proprietary extensions.

A skill is a folder with a `SKILL.md` file and optionally scripts. Directory-namespaced at arbitrary depth: `relay-os/skills/<path>/SKILL.md`.

```markdown
---
name: brand-voice
description: Use for any external communication — posts, emails, newsletters, replies.
---

# Brand voice

## Tone
- Direct, not corporate
- Technical but accessible
- Opinionated — we have a point of view

## Rules
- First person plural ("we") for company voice
- No exclamation marks in headlines
- Always cite specific data over vague claims
```

Frontmatter has `name` and `description`. That's it. The body is free-text knowledge — whatever the agent needs to understand the domain.

Skills with scripts bundle knowledge and tooling together:

```
relay-os/skills/content/linkedin/
  SKILL.md      ← API specs, rules, payload format
  post.py       ← script to actually post (agent calls directly, or executed via mode: script)
```

The agent reads the SKILL.md to understand what to do, and calls the script directly during its session (interactive/auto) or the script is executed by `relay launch` when the task uses `mode: script`.

Skills are pure knowledge. They don't define process or who runs them — that's what workflows do.

---

### Contexts

Contexts are domain knowledge — facts about the world the task operates in. Same file format as skills (`SKILL.md` standard), same arbitrary-depth nesting, stored in a sibling directory: `relay-os/contexts/<path>/SKILL.md`.

The distinction between skills and contexts is functional, not just organizational:

- **Skills** are process knowledge — how to do things. They attach to **workflow steps**. A skill can include scripts (e.g., `post.py`). Example: `infra/testing-conventions` — how we write and run tests.
- **Contexts** are domain knowledge — what's true about the world. They attach to **tickets**. Pure knowledge, no scripts. Example: `email/payment-flow` — retry behavior after 429s, Stripe webhook edge cases, fraudster timing patterns.

This maps to how humans think about tasks: when designing a workflow, you ask "what process does each step need?" (skills). When creating a task, you ask "what does the agent need to know about this domain?" (contexts).

Contexts use the same `SKILL.md` format with `name` and `description` frontmatter. They are composed into the prompt at launch time by `relay launch`, not baked into the blackboard at creation time.

```
relay-os/contexts/email/payment-flow/
  SKILL.md      ← domain knowledge about payment behavior and edge cases
```

Tickets reference contexts in frontmatter:

```yaml
contexts:
  - email/payment-flow
```

Skills are not referenced in ticket frontmatter — they flow through workflow steps only.

---

### Workflows

Workflows are process definitions. A workflow defines an ordered sequence of steps from creation to done, and what knowledge each step needs.

Workflows live in `relay-os/workflows/` as markdown files at arbitrary depth. YAML frontmatter has the machine-parsable step list. Each step has a `name` and optionally a `skill` reference. Steps without a `skill` use inline instructions from the markdown body, keyed by heading.

`relay-os/workflows/code/with-review.md`:

```markdown
---
name: code/with-review
description: Standard code workflow with PR and approval gate.
steps:
  - name: implement
    skill: infra/testing-conventions
  - name: pr
  - name: approve
    skill: process/approve
  - name: merge
---

## pr
Create a branch, push, open a PR.

## merge
Merge the PR and clean up the branch.
```

`relay-os/workflows/content/post.md`:

```markdown
---
name: content/post
description: Content creation with approval before publishing.
steps:
  - name: draft
  - name: approve
    skill: process/approve
  - name: publish
---

## draft
Write a first draft in the task folder.

## publish
Post the content using the appropriate skill script.
```

Two ways to define what a step does:

- **`skill:` reference** — points to a real skill in `relay-os/skills/`. Full knowledge inlined when the task reaches that step. Use for reusable, rich instructions (code standards, approval criteria, etc.).
- **Inline instructions** — a heading in the markdown body matching the step name. One-liner for simple stuff. Use when the step is self-explanatory.

Key design decisions:

- **No `run` field on steps.** Workflows don't define who does the work. The `assignee` field on the ticket controls that. The same workflow can be used by a human or an agent — reassignment is a deliberate action on the ticket.
- **No mandatory steps.** You compose the workflow you need.
- **Steps are skills or one-liners.** Same step can be a full skill in one workflow and an inline sentence in another, depending on how much knowledge the agent needs.
- **Workflows are frozen into tickets at creation.** The ticket gets a snapshot of the workflow, not a reference. In-flight tickets are not affected by workflow changes. For v1, manually edit ticket frontmatter to update a frozen workflow.

When a task uses `--workflow code/with-review`, it starts at step 1. `relay step` moves to the next step. Tasks without a `--workflow` flag have no steps — they move through statuses directly.

---

### Control plane and data plane

A ticket has two independent state machines.

**Control plane (status)** governs *whether* work happens — scheduling, prioritization, lifecycle. Universal across all projects. Same states everywhere.

| Status | Meaning |
|---|---|
| `design` | Not ready. Needs scoping, research, or spec work before it can be executed. |
| `ready` | In the pool. Pickable. Work can start. |
| `active` | Someone is working on it. Workflow steps advance. |
| `paused` | Suspended. Workflow frozen at current step. Pick up later. |
| `done` | Completed. |
| `canceled` | Deliberately abandoned. |
| `failed` | Work was attempted and did not succeed. |

Transitions are not constrained by the system in v1 — any status can move to any other. The convention is:

- `design → ready → active → done`
- `active → paused → active` (resume)
- `active → design` (send back, needs rethinking)
- `active → failed` / `active → canceled`

Per-project config controls the default starting status via `default_status` in `relay.toml`.

**Data plane (workflow step)** governs *what* work happens — the sequence of steps to complete the task. Per-task, frozen from the workflow definition at creation time. Step only advances when status is `active`. Pausing freezes the step. Sending back to `design` does not reset the step.

---

### Task directory and the blackboard

**Tasks are directories, not files.** Each task lives in `relay-os/tasks/<id>-<slug>/` and contains:

```
003-fix-retry-logic/
  ticket.md             ← assignee, status, workflow step, description, context
  log.md                ← append-only structured log (written by CLI commands only)
  blackboard.md         ← shared workspace for human and agent
  task.lock             ← serializes concurrent access to all task files
```

**Single lock.** `task.lock` serializes writes to all files in the task directory. Under the one-task-one-worker constraint, a separate lock per file is unnecessary complexity.

**One task, one worker.** A task has exactly one assignee at a time — one human or one agent. Multiple workers never write to the same task concurrently. This is a deliberate v1 constraint for small teams (2-5 people). It means the lock file doesn't need to handle contention beyond accidental overlap (e.g., a human and an agent both running a CLI command on the same task at the same moment).

**Locks are local-only.** Lock files use file existence on the local filesystem. They serialize concurrent access on a single machine — they do not provide distributed locking across machines. This is sufficient under the one-task-one-worker constraint: if Marc's agent is working on task 003, Pierre's agent is not. Git merge conflicts on lock files are not expected in normal operation. If they occur, delete the lock and re-acquire — the dream/drift validation script covers stale lock detection.

**log.md** is append-only and structured. Written exclusively by CLI commands as a side effect — `relay launch`, `relay step`, `relay panic`, and `relay create` all append to `log.md` when they execute. Agents and humans do not write to `log.md` directly. If agents need to record unstructured observations, they write to the blackboard. Format:

```
2025-01-14 10:32 [agent:claude1] advanced to step 2 (pr)
2025-01-14 11:01 [human:marc] approved
2025-01-14 11:04 [agent:claude1] started merge
```

#### The blackboard

The blackboard pattern originates in AI research (Hearsay-II, CMU, 1970s) for problems where multiple independent specialist processes need to cooperate without direct coupling. The idea: all processes share a mutable workspace. One writes a partial result; another reads it and builds on it; a third sees the combined state and fires. Coordination is emergent — no process talks directly to another.

Relay applies this pattern per task. `blackboard.md` is the shared workspace for the task. Any entity — human or agent — can write to it at any time (serialized via `task.lock`). There is no message passing between human and agent; they communicate through the board.

**blackboard.md is unstructured.** V1 ships a minimal template — a title line and a one-line invitation to write — and lets the task fill it however serves the work. The protocol teaches the agent what's worth capturing (plans, findings, decisions with reasons, blockers) and to date-stamp non-trivial entries, but does not impose section headings. Imposing structure up front cost more in agent confusion than it bought in selective-load efficiency, so the API is "write whatever helps the next session pick up."

The blackboard is a workspace for live state — not a copy of the task's context. Domain knowledge and task-specific context live in the ticket (frontmatter context refs + inline body) and get composed into the prompt at launch time by `relay launch`. The blackboard captures what's happened *during* work. This avoids duplication between the blackboard and the composed prompt.

The default template:

```markdown
# Blackboard — {{task.id}} {{task.title}}

> Generated by relay at task creation.
> Open to human and agent writes. Write whatever helps the next session pick up.
```

**No separate archive file.** Git history is the archive. When the blackboard is rewritten, `git log` shows what was there before. This removes a file and a convention that agents would likely forget to follow.

---

### Ticket format

`ticket.md` — YAML frontmatter for machine-parsable fields, markdown body for human-readable content.

**Design principles:**

- **Ticket is source of truth.** Everything about the ticket's current state lives in `ticket.md`. No derived state computed from external files. The workflow is frozen into the ticket at creation — a snapshot, not a reference.
- **Nothing is required.** All frontmatter fields are optional. A ticket with just a title and status is valid.
- **Description vs Context in the body is for humans.** The agent reads the composed prompt, not the ticket body directly. The two sections exist to help humans organize their thinking: what to do (Description) vs task-specific knowledge (Context).

**Frontmatter fields:**

| Field | Type | Description |
|---|---|---|
| `title` | string | Human-readable name. No `id` field — the task directory path is the unique identifier. |
| `status` | string | Control plane. One of: design, ready, active, paused, done, canceled, failed. |
| `mode` | string | `interactive`, `auto`, or `script`. Default: `interactive`. Controls how `relay launch` starts work. `interactive`: human-attended session — agent starts with composed context, human present in terminal. `auto`: autonomous execution — agent receives composed context as one-shot prompt, runs without human input. `script`: direct execution — no agent spawned, script runs with secrets injected as env vars. |
| `owner` | string | Human accountable. Stable over the task's life. |
| `assignee` | string | Who's currently doing the work. Human name or agent nickname. Set independently — not derived from workflow. |
| `watchers` | list | Additional people who receive Slack @mention notifications. Owner and assignee auto-watch implicitly. |
| `workflow` | object | Frozen snapshot of the workflow at creation. Contains `name` (string) and `steps` (list of {name, skill?}). |
| `step` | string | Current position in frozen workflow. Format: `N (step-name)`. Only advances when status is `active`. |
| `contexts` | list | Paths to context references in `relay-os/contexts/`. Domain knowledge scoped to this task. |

**Body sections:**

- **Description** — what to do and why. The task definition.
- **Context** — task-specific knowledge that isn't a reusable skill or context file. One-off details: where in the codebase, what to watch out for, what not to touch.

`relay create` scaffolds the task directory with ticket.md (from CLI args and workflow snapshot), an empty blackboard.md (from the default template), and an empty log.md. Context is not baked into the blackboard — it's composed fresh into the prompt at launch time by `relay launch`. Skills are not read from the ticket — they flow through workflow steps at launch time.

**Full ticket example:**

```markdown
---
title: Fix retry logic
status: active
mode: interactive
owner: marc
assignee: claude1
watchers:
  - pierre
workflow:
  name: code/with-review
  steps:
    - name: implement
      skill: infra/testing-conventions
    - name: pr
    - name: approve
      skill: process/approve
    - name: merge
step: 1 (implement)
contexts:
  - email/payment-flow
---

## Description

Stripe webhook retries are silently failing after the third attempt.
The retry backoff logic doesn't account for rate-limit responses (429).
Fix the backoff to respect Retry-After headers and add observability
so we know when retries are exhausted.

## Context

The retry logic lives in `lib/webhooks/retry.ts`. Current backoff is
fixed 1s/5s/30s — no awareness of rate limit headers. The Stripe
dashboard shows ~40 exhausted retries/day, mostly on billing-update.
Don't touch the idempotency layer — that's a separate task.
```

**Minimal ticket (no workflow):**

```markdown
---
title: Look into slow DNS resolution on staging
status: ready
owner: marc
---

## Description

Staging DNS lookups are taking 2-3s. Might be the resolver config.
```

**Recurring template example (auto by default):**

```markdown
---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
mode: auto
workflow: ops/check
assignee: claude1
owner: marc
contexts:
  - email/deliverability
project: email-tool
---

## Description

Run the full deliverability diagnostic suite.
Check SPF, DKIM, DMARC for all active domains.
Flag any new blacklist entries.
```

---

### Lock file format

`task.lock` follows standard Unix `.lock` convention — file existence is the lock. The file contains metadata for staleness detection:

```
holder: claude1
acquired: 2025-01-14T10:32:00Z
```

The dream/drift validation script reads the `acquired` timestamp to detect stale locks (likely a crashed agent). Two fields, that's it.

---

### Other concepts

**Agent instruction file.** Relay does not own or overwrite `CLAUDE.md` / `AGENTS.md` / `.cursorrules`. These files belong to the developer. Relay delivers composed context via CLI prompt injection at launch time — the agent receives everything it needs as a prompt argument, not by reading an instruction file. The instruction file is available as a fallback for agents that don't support CLI prompt injection (e.g. Cursor), in which case Relay appends a relay-managed section to the file.

**Prompt composition.** `relay launch` builds a single composed prompt containing: global rules, project context, ticket contexts, current workflow step skill, and the blackboard. This prompt is written to a temp file and passed to the agent via the appropriate CLI flag. The temp file is cleaned up after the session ends (interactive) or the command exits (auto). 

**Three launch modes.** Tasks declare their mode in ticket frontmatter (`mode: interactive`, `mode: auto`, or `mode: script`). Interactive (default): human-attended session. Auto: autonomous execution — agent runs to completion without human input. Script: direct execution — no agent, just a script with secrets injected. See `relay launch` spec below.

**Secrets.** Credentials in `relay.local.toml`, injected as env vars at launch time by `relay launch`.

**Global rules.** `relay-os/rules.md` inlined in every composed task.

**Launch** Relay made to be used with a human or autonomously. In human mode, it will launch a terminal with the prompt loaded already.



### Crash recovery

**Crash recovery is manual in v1.** If an agent crashes mid-task (session dies, machine reboots, process killed), the human is responsible for cleanup:

1. Check the blackboard for last known state — the agent should have been writing findings and decisions as it worked.
2. Check for stale locks — clear if the agent is no longer running.
3. Relaunch with `relay launch` — the composed prompt includes the blackboard, so the new session picks up from the last written state.

The blackboard is the persistence layer between sessions. An agent that writes to the blackboard frequently (findings, plan updates, decisions) is recoverable. An agent that doesn't write is not. The relay protocol system prompt includes instructions telling the agent to write to the blackboard after meaningful progress.

No automatic crash detection or restart in v1. The dream/drift validation script flags stale locks (suggesting a crash), but recovery is always human-initiated.

---

### Self-bootstrapping

The system improves itself using its own primitives. They are CLI commands executed as recurring tasks: they're regular tasks that use Relay's existing primitives.

#### Dream skill

A skill (`relay-os/skills/meta/dream`) that tells the agent: scan the repo and improve skills and context.

The agent reads all tickets, blackboards, contexts, skills, and workflows. It looks for:

- Context gaps — tickets that reference domain knowledge with no matching context. Patterns that repeat across tickets but aren't captured anywhere.
- Skill gaps — workflow steps with no skill, or steps where the blackboard shows agents consistently struggling.
- Workflow gaps — groups of tickets that follow the same ad-hoc pattern but have no formalized workflow.
- Stale content — contexts or skills that contradict what's in recent blackboards.

Output: proposals written to the blackboard. Each proposal is a concrete suggestion — "create context `infra/retry-patterns` covering: ..." — not a vague recommendation. Human reviews and accepts or rejects.

Intended usage: a recurring task (`mode: auto`, scheduled weekly or ad-hoc) assigned to an agent. Standard `relay launch`.

It's also reading contexts and look for contradictions/things to resolve. It produces a report on Slack for the admin to check.

It's a persistent memory system (and we can probably use one of the opensource one) but it produces a report that a human is responsible for (to detect mistakes and contradictions).

#### Create-with-suggestions skill

A skill (`relay-os/skills/meta/create-suggest`) attached to the `create` workflow. When a human creates a task with a title and description, the agent:

1. Start from a template of ticket. 
2. Human explains what it's trying to do. Agents asks question until the ticket is filled.
3. Agent suggests which workflow fits, which contexts to attach, and which skills apply to each step.
4. Writes suggestions to the ticket frontmatter as a draft.
5. Human reviews and confirms.

This runs as part of `relay create` — after scaffolding, the agent is launched with the create-suggest skill to fill in the blanks. The human edits the result directly if needed.

#### Why this matters

These systems are very hard to bootstrap. By having agents do the initial work and maintain it, we ease the pain AND we follow our principle to keep everyting legible and open.

---

### Cron runner

Recurring tasks need a scheduler. Relay doesn't own the scheduler — the OS does. Relay provides the entry point.

`relay-os/scripts/cron.sh` is a script the user's system cron calls on a schedule. It:

1. Acquires a pidfile lock (`/tmp/relay-cron.pid`) — if another instance is already running, exit immediately. At most one cron run at a time.
2. Runs `relay create --check-recurring` — scans recurring templates in `relay-os/recurring/`, creates any due tasks.
3. Optionally runs `relay launch` on any newly created auto tasks — if the recurring template has `mode: auto`, the task can be launched immediately after creation.

The user sets up their own crontab:

```
# Check recurring tasks every hour
0 * * * * cd /path/to/relay-repo && relay-os/scripts/cron.sh
```

Relay provides the script. The user controls the schedule. No daemon, no background process, no relay-managed scheduler. If the machine is off, nothing runs. If the cron fails, it fails loud (stderr, non-zero exit). The next run picks up any tasks that were due but missed.

This keeps the "no server, no daemon" constraint intact while closing the loop on recurring tasks.

---

## CLI commands

### Design principles

**Side effects only.** The CLI exists for operations that require side effects (Slack notifications, process spawning, logging) or validation. Everything else is direct file editing by humans or agents.

**No magic. Everything exposed.** Every command is callable by a human, even if it's primarily used by agents. There are no hidden internals. If you want to understand what an agent did, you can replay its commands with the same output and side effects. The distinction between "human commands" and "agent commands" is convention — who typically calls them — not access control.

**Foreground and background.** The CLI has a foreground (commands humans reach for daily) and a background (commands agents call, taught by the system prompt). Background commands are fully exposed — a human debugging a stuck task can call `relay step` or `relay panic` manually, see the same output, trigger the same side effects. Nothing is hidden; it's just layered. You learn the foreground first, discover the background when you need it.

### Commands

**Foreground** — what humans call:

| Command | What it does |
|---|---|
| `relay create` | Scaffold a ticket, snapshot the workflow into frontmatter. Also checks recurring templates and creates any due tasks. |
| `relay launch` | Compose prompt from all context, inject secrets, start work on a task. Handles all three modes: interactive, auto, and script. |
| `relay status` | Show all active tasks across projects. One line per task: project, id, title, assignee, step, mode. |

**Background** — what agents call (taught by the relay protocol system prompt):

| Command | What it does |
|---|---|
| `relay step` | Move task to next workflow step. Logs, notifies Slack. On the last step, marks the task done. |
| `relay panic` | Agent is stuck. Write blockers to blackboard, @mention the task owner in Slack, stop. |
| `relay feed` | Post an informational (FYI) message to the Slack channel. No @mention — just a line in the feed. |

### Who edits what

**Humans** edit files directly — reassign a task, adjust context refs, tweak a workflow, update skills. The dream/drift skill includes a validation script that checks repo consistency (stale locks, broken references, invalid state) as part of its recurring run.

**Agents** edit files directly — write to the blackboard, update frontmatter fields (contexts, blockers). Agents call background commands within their self-service boundary, as taught by the relay protocol system prompt.

---

### `relay launch` — decided spec

`relay launch --task <task-id>`

#### Behavior

1. Resolve the current user from `relay.local.toml`.
2. Look up the task in the specified project (or search across projects if unambiguous).
3. Read the `assignee` field from the ticket. Resolve the agent nickname in the user's `[assignees]` config to the agent type.
4. Verify the task's `status` is `active`. Error if not.
5. Load secrets from `relay.local.toml` `[secrets]` section. Resolve `env:VAR_NAME` references to actual values. These will be exported as environment variables into the launched process.
6. **Compose the prompt.** Assemble in this order:
   - Relay protocol system prompt (how to operate within Relay — see below)
   - Mode-specific protocol block (interactive vs. auto behavioral rules)
   - `relay-os/rules.md` (global rules)
   - `relay-os/context.md` (project base context)
   - Contexts referenced in ticket frontmatter (inlined from `relay-os/contexts/`)
   - Inline context from ticket body (the `## Context` section)
   - Current workflow step skill (inlined from `relay-os/skills/` if the step has a `skill:` reference, otherwise the inline instruction from the workflow markdown)
   - Blackboard (`blackboard.md`) — full contents
7. Write composed prompt to a temp file: `/tmp/relay-<task-id>-<timestamp>.md`
8. Read the `mode` field from the ticket. Default: `interactive`.
9. Launch based on mode:
   - **Interactive:** `{cli} {interactive-flag} /tmp/relay-<task-id>.md` — opens an interactive session with composed context loaded. Human is present.
   - **Auto:** `{cli} {auto-flag} "$(cat /tmp/relay-<task-id>.md)"` — sends composed prompt, agent runs to completion. CLI waits for exit.
   - **Script:** No agent spawned. Reads the current workflow step's skill, finds the script, executes it directly with secrets injected as env vars. No prompt composition, no LLM token cost.
10. Log the launch: append to `log.md` — `"launched in {mode} mode"`
11. Post to Slack via `relay feed`: FYI — `marc's claude1 started work on email-tool 003 "Fix retry logic" (interactive)`

#### Composition order

The order is deliberate — it follows specificity:

1. Relay protocol (how to operate — same for every task)
2. Mode-specific block (interactive vs. auto behavioral rules)
3. Global rules (broadest — apply to everything)
4. Project context (project-level — apply to all tasks in this project)
5. Contexts (domain knowledge — scoped to this task type)
6. Inline context (task-specific — one-off details for this exact task)
7. Workflow step skill (process knowledge — what to do right now)
8. Blackboard (live state — what's happened so far, decisions, findings)

Later content overrides earlier content when they conflict. The agent sees the most specific information last, which is where most LLMs place the highest weight. The protocol comes first because it's structural — it defines how the agent interacts with the system, not what it does. It should never be overridden by task-specific content.

#### Multi-task per project

`relay launch` requires `--task`. It launches exactly one task per invocation. If you have two active tasks in the same project, you launch them separately in separate terminal sessions.

#### Errors

| Scenario | Behavior |
|---|---|
| Task not found | Error. Show available tasks. |
| Assignee not found in current user's agents | Error. "Task 003 is assigned to `claude2`, which is not in your agent config." |
| Task status is not `active` | Error. "Task 003 is `paused`. Set to `active` before launching." |
| Agent CLI binary not found | Error. "{cli} not found in PATH." |
| Missing context or skill reference | Error. List the missing references. Do not launch. |
| Mode is `script` but no script found in step's skill | Error. "Step `publish` has no script to execute." |

---

### `relay panic` — decided spec

`relay panic --task <task-id> --reason "<text>"`

#### Behavior

Writes reason to the blackboard's Blockers section, @mentions the task owner in Slack, stops the agent. This is the only escalation mechanism for autonomous agents.

Example:

```
relay panic --task 003 --reason "429 retry logic unclear, need decision on backoff ceiling"
```

Slack: `@marc — email-tool 003 "Fix retry logic" — agent stuck: "429 retry logic unclear, need decision on backoff ceiling"`

`--reason` is required.

---

### `relay step` — decided spec

`relay step <next-step-number>`

A thin command for side effects. The agent calls this when it completes a workflow step. The intelligence about *when* to call it lives in the relay protocol system prompt, not in the command.

#### Behavior

1. Read the task's current step from ticket frontmatter.
2. Validate: task status must be `active`. Error if not.
3. Update the `step` field in ticket.md to the next step.
4. If this was the last step: set `status: done`, release the lock.
5. Append to `log.md` — `"advanced to step N (step-name)"` or `"task done"`.
6. Post to Slack via `relay feed`: FYI — step transition or task completion.

#### Errors

| Scenario | Behavior |
|---|---|
| Task is not `active` | Error. "Task 003 is `paused`. Cannot advance." |
| Task has no workflow | Error. "Task 003 has no workflow steps." |
| Already on last step | Not an error — marks task `done` and notifies. |

---

### Repo consistency checks

Repo validation (stale locks, broken references, invalid status values, stuck tasks) is handled by a deterministic validation script, not an LLM. This script is part of the dream/drift skill — the skill runs the script, then the agent interprets the output alongside its broader scan for knowledge gaps, stale content, and workflow patterns.

Checks include:

- Task directories have all required files (ticket.md, log.md, blackboard.md)
- Lock is not stale (held for unexpectedly long — likely a crashed agent)
- Tasks stuck in `active` status with no recent log activity
- Workflow step references point to skills that actually exist
- Context references in tickets point to contexts that actually exist
- Assignees in task files match known users in `relay.toml`
- Status values are valid (one of: design, ready, active, paused, done, canceled, failed)

---

## Relay protocol — system prompt

The relay protocol is a system prompt injected at the top of every composed prompt by `relay launch`. It teaches the agent how to operate within Relay — not what to do (that comes from skills, contexts, and the ticket), but how to behave as a participant in the system.

This is the most important piece of the spec. When commands like `relay step` were thinned to pure side-effect runners, the protocol became the brain — it carries the logic about when to advance, when to panic, how to use the blackboard, and how to handle frontmatter.

### What the protocol covers

1. **Identity** — you're an agent working on a ticket inside Relay.
2. **Files** — what ticket.md, blackboard.md, and log.md are for. Which you read, which you write, which you don't touch.
3. **Blackboard discipline** — write frequently (plan, findings, decisions, blockers). The blackboard is the crash recovery mechanism. An agent that writes to it is recoverable; one that doesn't is not.
4. **Step transitions** — do the work for your current step. When done, call `relay step`. Do not skip steps. Do not go back. If a previous step needs rework, panic.
5. **Escalation** — call `relay panic` when stuck. Be specific about the reason. Write to the Blockers section before panicking. After panicking, stop.
6. **Feed** — call `relay feed` for FYI updates. Keep messages short. Do not use feed for blockers.
7. **YAML discipline** — preserve existing fields, use exact syntax, don't invent formats.

### Mode-specific blocks

The protocol has a base section (same for every task) and a mode-specific block swapped in by `relay launch`:

**Interactive block:** You're working with a human. Ask when uncertain. Discuss tradeoffs. The human is here.

**Auto block:** You're alone. Either proceed (and note uncertainty on the blackboard) or panic. Do not write questions and wait — nobody is watching.

The `script` mode does not use the protocol — no agent is spawned.

### Why this matters

Before the protocol, agents needed to know Relay's conventions through their instruction file (CLAUDE.md, AGENTS.md) or through ad-hoc prompting. This was fragile — every agent type needed separate instructions, conventions drifted, and there was no guarantee the agent knew how to use the blackboard or when to escalate.

The protocol standardizes this. Every agent, regardless of type, receives the same operating instructions at launch time. The instructions are version-controlled, editable, and visible — consistent with the "no magic, everything exposed" design principle.

### Prompt templates replaced

The earlier spec flagged "prompt templates for agent file editing" as a blocking dependency. The relay protocol resolves this — it teaches YAML formatting rules, blackboard conventions, and file discipline directly in the system prompt. No separate template system needed.

### Location

The relay protocol lives at `relay-os/protocol.md` (base) and `relay-os/protocol-interactive.md` / `relay-os/protocol-auto.md` (mode blocks). Version-controlled alongside skills, contexts, and workflows.

---

## Slack feed

**What:** A live activity feed in a shared Slack channel. Every state change across the company posts automatically. Humans get @mentioned when they need to act. Everything else is FYI.

**Why:** Agents work asynchronously. Humans need to know when something needs their attention (review, approve, unblock) and what their agents have been doing. The Slack channel is the primary awareness layer — a scrollable timeline of everything happening across all projects.

### Design principles

The assumption is to overshare. Every state-changing CLI command posts to Slack. No filtering, no agent decision-making about what's "worth" notifying. The channel is a complete feed. If it ever gets too noisy, that's a good problem — it means a lot is getting done, and we can dial back then.

The shared channel is deliberate: team-wide visibility and mutual accountability. Everyone sees what's moving.

### Two tiers

Messages use two tiers to separate "you need to act" from "FYI":

- **@mention** — human action needed. The person is tagged and expected to respond. Triggers when the assignee changes to a human, or when an agent panics.
- **Plain text** — informational. No tag, just a line in the feed.

### What posts and when

| Event | Posts | Tier |
|---|---|---|
| `relay create` | New task created | FYI |
| `relay launch` | Agent started work on task (includes mode) | FYI |
| `relay step` | Task moved to next step (or completed on last step) | FYI |
| `relay panic` | Agent stuck, needs human | @mention to task owner |
| `relay feed` | Custom FYI message from agent (e.g. "opened PR #142") | FYI |

Ticket-related notifications (assignment changes, status changes) follow the same two-tier model. Owner and assignee auto-watch every task they're on — no explicit subscription needed. Watchers in the ticket frontmatter are additive — they receive @mentions on the same triggers.

### Notification logic lives in the CLI

The agent calls `relay step`, etc. as normal. The CLI decides what to post and whether to @mention. Agents never reason about what's worth notifying — the commands themselves are the notification hooks.

### Delivery

Shared Slack channel via the incoming webhook configured in `relay.toml`. The webhook is channel-bound.

To @mention users, the CLI needs a mapping from relay usernames to Slack user IDs. This lives in the `[assignees]` config.

### Message format examples

```
@marc — email-tool 003 "Fix retry logic" needs your attention (approve, step 3)

marc's claude1 completed step 2 (pr) on email-tool 003 "Fix retry logic"

New task: content 005 "LinkedIn post retry logic" assigned to marc (workflow: content/post)

marc's claude1: pushed branch, opened PR #142 (email-tool 003)

email-tool 003 "Fix retry logic" done ✓

@marc — email-tool 003 "Fix retry logic" — agent stuck: "429 retry logic unclear"
```

---

## Error model

Every CLI command can fail. The spec describes happy paths — this section defines failure behavior.

**General principles:**

- **Fail loud, fail early.** CLI exits with a non-zero code and a human-readable error message. No silent failures. No partial state changes — if a multi-step command fails partway, it should either roll back or leave a clear trail of what completed and what didn't.
- **Agents see errors too.** When an agent calls `relay step` or `relay panic` and it fails, the agent sees the stderr output. Error messages should be actionable enough that an agent can log the failure and flag it, or retry if appropriate.
- **Slack gets notified on failures that matter.** If `relay launch` fails with `mode: script` (script exits non-zero), or `relay step` fails on an active task, post to the Slack feed so the human knows.

**Specific failure cases:**

| Scenario | Behavior |
|---|---|
| Lock can't be acquired (already held) | Error with holder identity and acquisition time. Agent/human decides whether to wait or force. `--force` flag to break stale locks. |
| `relay launch` with `mode: script` exits non-zero | Log the failure to log.md. Post to Slack. Task stays at current step. |
| `relay step` on a non-active task | Error. Task must be `active` to advance. |
| `relay create` with missing context/skill references | Error. List the missing references. Do not create the task. |
| `relay create` with missing project path | Error. The project path in `relay.local.toml` must exist. |
| `git push` rejected | Show the git error. Suggest `git pull --rebase` then retry. Do not auto-resolve. |

Note: `relay step` on the last step is not an error — it marks the task `done` and notifies. See `relay step` spec.

---

## V2 backlog

Items to evaluate after v1 is built and used. Not designed yet.

1. **Per-project control plane workflows.** The universal status list (design, ready, active, etc.) could become an editable state graph per project — same workflow primitive as the data plane, but with branches and backward edges. Requires extending the workflow format to support non-linear graphs.
2. **Priority / ordering.** Skipped for v1. If 15+ active tasks across projects makes it hard to know what to work on next, add then.
3. **Real Slack app.** Bot token with `chat:write` + `users:read` scopes for DMs instead of shared channel @mentions.
4. **Fully autonomous agent chains.** Agent-to-agent handoff: when agent A completes its step and the next step is assigned to agent B, auto-trigger `relay launch` for B. Requires lifting the `reassign`-to-agent restriction. Depends on v1 learnings about how often multi-agent chains actually occur.
5. **System-prompt-level injection for Codex/OpenCode.** Currently `interactive` and `auto` use the same subcommand for these tools because they lack `--system-prompt` flags. When these tools add them, update agent config to prefer system-level injection.
6. **`relay update-workflow`.** Re-snapshot a workflow definition into an in-flight ticket's frontmatter while preserving the current step position. Useful when workflow definitions change frequently during iteration. For v1, manually edit ticket frontmatter instead.

---

## Removed

**`relay inbox`** — removed. The Slack feed is the notification layer. No local inbox command.

**`run` field on workflow steps** — removed. Workflows don't define who does the work. The `assignee` field on the ticket controls that. Slack @mentions trigger on assignee changes (when the new assignee is a human), replacing the old `run: human` trigger.

**`created` field in ticket frontmatter** — removed. The first log entry is the source of truth for when the ticket was created.

**`recurring` status** — removed. Recurring tasks are handled by templates in `relay-os/recurring/` with cron schedules, not by a task status. A completed recurring task is `done`. The template creates a fresh task on the next cycle. Scheduling is a concern separate from task lifecycle.

**`skills` in ticket frontmatter** — removed. Skills attach to workflow steps, not tickets. Contexts attach to tickets. This gives a functional distinction: skills = process knowledge flowing through workflows, contexts = domain knowledge scoped to a task.

**`relay reassign`** — removed. Human-to-human reassignment is done by editing the `assignee` field in ticket frontmatter directly. Agent escalation is handled by `relay panic`.

**`relay done`** — absorbed into `relay step`. Stepping past the final step sets status to `done` and notifies.

**`relay log`** — removed from CLI. Log entries are written by CLI commands as internal side effects. Agents and humans do not write to `log.md` directly — use the blackboard's Notes section for unstructured observations.

**`relay status`** — moved to convenience command. Shows one-line-per-task summary across projects.

**`relay run`** — removed. Absorbed into `relay launch`. Script execution is handled by `mode: script` — `relay launch` reads the step's skill, finds the script, runs it directly with secrets injected as env vars. No separate command needed; the agent calls scripts natively during interactive/auto sessions.

**`relay recurring`** — removed. Absorbed into `relay create`. `relay create` checks recurring templates and creates any due tasks. A cron job or human runs `relay create --check-recurring` on a schedule.

**`relay check`** — removed as standalone command. Repo validation (stale locks, broken references, invalid state) is now a deterministic script inside the dream/drift skill. The skill runs the script, the agent interprets the output.

**`relay sync`** — removed. Was a ghost reference in the error model with no spec. Git push/pull is manual.

**`relay advance`** — renamed to `relay step`. Thinned to a side-effect command (update step field, log, notify Slack). The intelligence about when to advance lives in the relay protocol system prompt, not the command.

---

## Still underspecified — needs design before or during v1 build

### Blocking — must resolve before building

#### `relay create`

No detailed behavior spec. Now also absorbs recurring template checking. Open questions:

- Which frontmatter fields are set automatically vs. passed as CLI args?
- How does create-with-suggestions integrate? Is it a post-create hook? A flag?
- Handling of duplicate context references.
- Skills from workflow steps are not composed at creation time — they are loaded at launch time for the current step. Confirmed, but the boundary needs to be explicit in the spec.
- Recurring integration: how does `relay create --check-recurring` detect "already created for this period" — naming convention on created task, or `last_run` field updated in the template?
- What "due" means for different schedule frequencies (daily, weekly, monthly).

#### ~~Task ID generation~~ — resolved

Per-project auto-increment. Each project directory has a `relay-os/counter` file containing the next task ID as a plain integer. `relay create` reads, increments, and writes this file atomically (file lock around the read-write). Format: `003-fix-retry-logic` — zero-padded to 3 digits, slug auto-generated from title (lowercase, hyphens, truncated to 50 chars). The ID is stable — used in branch names (`relay/003-fix-retry-logic`), Slack messages, and cross-references. Concurrent creation collisions are handled by the same lockfile used for the counter read-write — second caller waits.

#### `relay create` CLI interface

The command's arguments are not defined. Open questions:

- What's the invocation? `relay create --project email-tool --workflow code/with-review --title "Fix retry logic"`? Interactive prompts? A mix?
- Which arguments are required vs. optional?
- The create-with-suggestions skill implies a conversational post-create flow, but the base command needs a defined argument interface before that can layer on top.

#### Lock lifecycle

Lock format is defined (holder + acquired timestamp, file-existence based). The acquire/release lifecycle is not. Open questions:

- When is the lock acquired? By `relay launch`? By the first CLI command the agent calls?
- When is it released? On process exit? On `relay step` to `done`? On `relay panic`?
- What happens on Ctrl+C in interactive mode — is release tied to a signal handler?
- Does `mode: script` acquire a lock?
- Stale lock detection threshold — how long before the dream/drift script considers a lock stale?

#### Interactive and auto protocol blocks

The base protocol (`relay-os/protocol.md`) is written. The mode-specific blocks (`protocol-interactive.md` and `protocol-auto.md`) are described in one sentence each but the actual prompt text doesn't exist. These are a hard dependency for `relay launch` — prompt composition includes them.

### Should resolve — but won't block initial build

#### `relay panic`

Described briefly but not at the level of `relay launch`. Missing:

- Full error table (what if task has no owner? what if agent is in interactive mode? what if the task isn't active?).
- Exact format of the Blockers section write.
- Does panic change the task status? (e.g. to `paused`?)

#### Step transitions with assignee changes

When `relay step` advances to a step where a different person should take over (e.g. implement → approve), what happens? Does the system prompt teach the agent to reassign? Does `relay step` handle it? This is especially important for the approve step pattern.

#### Task lifecycle transitions

- What happens to the workflow step when status moves to `paused` then back to `active`? (Expected: resumes at same step. Confirm.)
- What happens to the workflow step when status moves to `design`? (Expected: preserves step. Confirm.)
- Should invalid transitions be rejected or just warned about by the dream/drift validation script?

#### Workflow-less tasks

- Tasks without a `workflow` field use simple status transitions (no steps).
- Interaction with `relay step` (error? no-op?).
- How do they appear in `relay status`?

#### `step` field management

- If someone manually edits the step field, what happens? Is the ticket the source of truth even for manual edits?
- Format `N (step-name)` — is N 1-indexed?

#### `relay status` — detailed behavior

Listed as a foreground command but has no spec beyond "show all active tasks across projects." Open questions:

- What does the output look like? Columns, formatting?
- Does it scan all projects or just the current one?
- Filters: by project, by assignee, by status?
- Sorting: by project, by recency, by status?
- Does it show only `active` tasks, or all non-done tasks?

#### `relay feed` — detailed behavior

Listed as a background command but has no spec beyond the protocol description. Open questions:

- Does it require `--task`? (Likely yes — agent is always working on a task.)
- Does the message format include task/project context automatically, or does it post the raw string?
- Is there a character limit?

#### Script mode execution path

`relay launch` with `mode: script` says "finds the script, executes it directly." The error table covers "no script found" but the happy path is thin. Open questions:

- How does it find the script — first executable in the skill directory? A `script` field in the skill frontmatter?
- What's the working directory — the project root? The task directory?
- What if the step has inline instructions instead of a `skill:` reference — is that an error for script mode?
- Exit code handling beyond non-zero = failure?

#### Project / task resolution

`relay launch` says "search across projects if unambiguous." Open questions:

- Is `--task` just the numeric ID, or `project/id`?
- What's the error message on ambiguity — does it list the colliding tasks?
- Do other commands (`relay step`, `relay panic`, `relay feed`) also need `--task`, and do they resolve the same way? Or do they infer the task from the current working directory / active session?

### Can defer — resolve during or after 3-month internal use

#### Archival / cleanup of done tasks

- Do done tasks accumulate in `relay-os/tasks/` forever?
- Is there a prune or archive command? Auto-cleanup after N days?
- Will know what's needed after 3 months of use.

#### `relay init` / `relay project add`

- Setup commands. Not spec'd beyond listing.
- Manual repo setup works for v1.

#### Task dependencies

- No structured way to say "task B blocked by task A."
- The Blockers section on the blackboard is freeform.
- Likely sufficient for v1 at this team size.

#### Context/skill staleness

- No mechanism to flag stale skills or contexts beyond the dream skill's periodic scan.
- Dream skill likely handles this. Revisit if it doesn't.

#### Git merge conflicts

Git is the sync layer. The one-task-one-worker constraint means two people rarely touch the same task files. Conflicts are most likely on `relay.toml` (config edits), simultaneous `relay create` (task ID collision), or rare human-edits-while-agent-pushes cases. Manually resolved for v1.

#### Prompt size / token limits

No detection or mitigation when the composed prompt exceeds the agent's context window. A task with multiple contexts, a rich skill, a long blackboard, and a detailed ticket body could exceed limits. Likely fine for v1 with small context sets — but worth a conscious decision about whether to warn, truncate, or ignore.

#### Blackboard growth

Over a long-running task with many relaunches, the blackboard grows unbounded. Plan is "live state" (replaced), but Findings, Decisions, and Notes accumulate. Eventually competes for context window space. No pruning or summarization strategy. May not matter for v1 task durations — revisit if tasks routinely span 10+ sessions.

#### Temp file cleanup

Composed prompt is written to `/tmp/relay-<task-id>-<timestamp>.md`. Spec says "cleaned up after the session ends (interactive) or the command exits (auto)." Crashes leave orphans. Probably harmless (`/tmp` is ephemeral on most systems) but unaddressed.
