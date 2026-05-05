# Relay CLI — spec (consolidated)

This document merges `relay-spec-v2` and all updates from `relay-spec-updates` into a single source of truth.

---

> **Scope.** Reference contract for config schemas, frontmatter shapes, the foreground command surface, and error/failure tables. Open this when *implementing* config, frontmatter, or CLI changes — it has the detail the contexts don't.
>
> The mental model (primitives, planes, prompt composition, locking) lives in [`relay-os/contexts/relay/architecture/`](../relay-os/contexts/relay/architecture/SKILL.md) and is what tickets load at launch. If the two contradict, `architecture` is canon and the spec entry is a bug — file a reconcile ticket rather than implementing from the spec.

---

## `relay.toml`

```toml
version = 1
default_status = "draft"

# --- Agents ---

[agents.claude]
cli = "claude"
interactive = "--append-system-prompt-file"
auto = "-p"
file = "CLAUDE.md"
mode = "local"

[agents.codex]
cli = "codex"
interactive = ""
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

[assignees.pierre]
agents = {"claude2": "claude", "goat": "copilot"}

# --- Slack ---
# The webhook URL itself lives only in $SLACK_WEBHOOK_URL (a bearer
# token; never commit it). The toml only carries the opt-out toggle:
# omit the block to leave Slack required (default), or set
# enabled = false in relay.local.toml to opt out.

# [slack]
# enabled = false  # in relay.local.toml only — disables Slack for this user

# --- Aliases ---
# Sugar for the often-used commands. Maps a one-word name to an
# expanded relay command. Positional args after the alias name forward
# to the expansion. Default aliases shipped by `relay init`:

[aliases]
chat = "launch bootstrap/orient"
# Optional once the current user has these nicknames configured:
# claude = "launch bootstrap/orient --agent claude1"
# codex = "launch bootstrap/orient --agent codex1"
create = "launch bootstrap/ticket"
```

### Agent config fields

| Field | Description |
|---|---|
| `cli` | Binary name. |
| `interactive` | Flag/subcommand for human-attended sessions. Agent starts with composed context loaded; human is present in terminal. For Claude Code: `--append-system-prompt-file` loads the composed context as system-level instructions while keeping an interactive session open. |
| `auto` | Flag/subcommand for autonomous execution. Agent receives composed context as a one-shot prompt, runs to completion without human input. For Claude Code: `-p` sends the prompt and exits when done. |
| `file` | Instruction file (CLAUDE.md, AGENTS.md, etc.). Developer-owned — Relay does **not** overwrite it. Fallback for agents that don't support CLI prompt injection. |
| `mode` | `local` for now. Future: `remote`, `cloud`. |

### Aliases

`[aliases]` maps a one-word name to an expanded `relay` command. Positional
args after the alias name forward to the expansion. The expansion is
printed to stderr (`→ relay <expansion>`) before dispatch so the
indirection is visible.

Validated at config load — fail loud, not silent:

- Alias names cannot collide with built-in commands (`init`, `launch`,
  `status`, `bump`, `panic`, `slack`, `recurring`).
- The first token of the expansion must be a known built-in.
- Aliases are pass-through only. Arguments and flags after the alias name
  are forwarded to the expanded command.

For scripted task scaffolding (when you want full keyword control rather
than the alias's positional surface), call `scaffold_task()` in
`relay.scaffold`.

### `relay.local.toml` (gitignored, per machine)

```toml
user = "marc"

[secrets]
linkedin_token = "env:LINKEDIN_TOKEN"
linkedin_person_id = "env:LINKEDIN_PERSON_ID"
stripe_key = "env:STRIPE_SECRET_KEY"
reddit_client_id = "env:REDDIT_CLIENT_ID"
reddit_client_secret = "env:REDDIT_CLIENT_SECRET"
github_token = "env:GITHUB_TOKEN"
```

Shared config has the what, local config has the who-am-I and the credentials.

---

## Repo structure

Relay is a company OS — and **a Relay repo is one operational surface**. One repo per surface: a `code` repo for engineering work, an `admin` repo for legal/finance/hiring, a `company` repo for cross-cutting ops. Each one has its own `relay-os/` directory at the root and is independent — no federation, no cross-repo CLI commands, no shared task ID space. The CLI always operates on the relay-os/ in its working tree.

Everything the surface runs on lives in that one repo: code workflows, content ops, research processes, finance tasks, agent skills, the work artifacts themselves. Everyone on the team has full read access. No ACLs, no siloing. This is an explicit architectural decision for small, high-trust teams: the overhead of access control costs more than it protects. Credentials never live in the repo (see `relay.local.toml`).

Skills, workflows, and recurring templates all support arbitrary depth nesting. There is no fixed two-level `<domain>/<skill>` constraint — paths reflect the actual structure of the surface's knowledge.

```
~/work/code/                ← the repo IS the project
  .git/
  CLAUDE.md                 ← developer-owned, NOT overwritten by relay
  [code files...]
  relay-os/
    relay.toml              ← shared config (committed)
    relay.local.toml        ← gitignored — user, secrets
    rules.md                ← global rules, inlined in every task
    context.md              ← repo-wide context, inlined in every task
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
      bootstrap/
        dream/SKILL.md
        create/SKILL.md
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
    tasks/
      fix-retry-logic/      ← directory named by slug; no numeric prefix
        ticket.md           ← assignee, status, workflow step, description, context
        log.md              ← append-only, written by CLI commands only
        blackboard.md       ← shared workspace (see below)
        task.lock           ← serializes concurrent access
    bootstrap/
      create/
        ticket.md           ← persistent launch shim → `relay launch bootstrap/ticket`
    scripts/
      cron.sh               ← entry point for system cron
```

> **Multi-surface companies.** A team running multiple operational surfaces just keeps multiple repos — one per surface. Cross-surface visibility happens through Slack (every repo's webhook can post into the same channel), not through the CLI. There's no `relay status --across-repos` or equivalent; if you want a unified view of work, the Slack feed is it.

> **Future consideration:** contractor access and per-domain ACLs are not designed for now. If the team grows to include external contributors or lower-trust roles, a submodule-per-domain strategy is the likely path — one architectural seam rather than a full permission system.

> **Git as sync layer.** Git is the v1 sync mechanism — zero infrastructure, free versioning, works with existing developer workflows. This is a deliberate choice for small teams (2-5 people), not a permanent architectural commitment. At 10+ people or with real-time coordination needs, git push/pull becomes a bottleneck and merge conflicts on task files become frequent. A server-backed sync layer is the likely v2/v3 path. For now, conflicts are rare (see one-task-one-worker constraint) and manually resolved when they occur.

---

## Goals / Insights

- Small team 5-10 people
- Work for everything (not just code but marketing, etc.). CompanyOS — a repo of all tasks/processes
- The key problem for agents is knowledge management (understand what to know)
- It's easier to have a human manage KM — too important to leave to AI for recurring tasks and important ones
- Once you have figured out KM, then it's context loading
- Then it's task assignment + memory (for in between runs) and you want to move a task from an AI to a human and vice versa. Ticket is a good abstraction for that — it enriches the context
- Agents have an owner — they're bound to a person, not to a repo. A person can have multiple instances of the same agent type (e.g. two Claude Code sessions). Nicknames distinguish them. Dispatch key is always (user, nickname)

---

## Decided — key concepts

These are locked in. Not yet built, but the design is final.

**The repo is the project.** A Relay repo represents one operational surface. There is no `[projects.X]` block, no `--project` flag, no cross-repo task ID space. Multi-surface companies use multiple repos.

**Agents are types.** An agent type defines cli binary, instruction file, and mode. `[agents.claude]` is the template — it says "Claude Code uses `claude` cli, reads `CLAUDE.md`, runs locally." Agent types are not tied to a person or repo.

**Agent instances have an owner.** Each person owns named instances of agent types. Marc has "claude1" (type: claude), "claude2" (type: claude), "my IDE" (type: cursor). Pierre has "claude2" (type: claude), "goat" (type: copilot). Nicknames are per-person — no global collision. The dispatch key is always `(user, nickname)`. `relay launch claude1` resolves the current user from `relay.local.toml`, finds their "claude1", and uses the `claude` agent type config.

**Assignees are humans.** Humans own agent instances and are the `owner` of tasks. The `assignee` field on a ticket is who's currently doing the work — a human name or an agent nickname. Reassignment is a deliberate action, not an automatic flip. The ticket is the source of truth for who's assigned.

---

### Skills

Skills are knowledge. They follow the `SKILL.md` standard — the same format used by Claude Code and OpenAI Codex. A relay skill IS a Claude Code skill IS a Codex skill. Zero proprietary extensions, which means tools that already speak SKILL.md — Anthropic's `skill-creator`, IDE skill browsers, anything else built around the standard — work on relay skills out of the box.

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

Frontmatter has `name` and `description` for ordinary skills. Executable
skills may also declare `script: <filename>` so `mode: script` can run the
tooling directly. The body is free-text knowledge - whatever the agent needs to
understand the domain.

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

Workflows live in `relay-os/workflows/` as markdown files at arbitrary depth. YAML frontmatter has the machine-parsable step list. Each step has a `name`, optionally a `skill` reference, and optionally an `assignee` role token (one of `owner` | `human` | `agent`). Steps without a `skill` use inline instructions from the markdown body, keyed by heading.

`relay-os/workflows/code/with-review.md`:

```markdown
---
name: code/with-review
description: Standard code workflow with PR and approval gate.
steps:
  - name: implement
    skill: infra/testing-conventions
    assignee: agent
  - name: pr
    assignee: agent
  - name: approve
    skill: process/approve
    assignee: human
  - name: merge
    assignee: owner
---

## pr
Create a branch, push, open a PR.

## merge
Merge the PR and clean up the branch.
```

The `assignee:` field on a step is a *role token*, not a literal nickname. On bump into a step that declares one, the ticket's `assignee:` is rewritten to whatever the ticket's matching role field (`owner:`, `human:`, `agent:`) holds. Role tokens — not literals — keep the workflow reusable across tickets with different humans and agents. Steps that omit `assignee:` leave the ticket's assignee unchanged on bump (back-compat for older workflows).

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

- **Steps name a *role*, not a person.** A step's `assignee:` field takes a role token (`owner` | `human` | `agent`) — never a literal nickname. The ticket carries the concrete `owner:` / `human:` / `agent:` fields, and bump resolves the token against them. The same workflow stays reusable across tickets with different humans and agents.
- **No mandatory steps.** You compose the workflow you need.
- **Steps are skills or one-liners.** Same step can be a full skill in one workflow and an inline sentence in another, depending on how much knowledge the agent needs.
- **Workflows are frozen into tickets at creation.** The ticket gets a snapshot of the workflow, not a reference. In-flight tickets are not affected by workflow changes. For v1, manually edit ticket frontmatter to update a frozen workflow.

When a task uses `--workflow code/with-review`, it starts at step 1. `relay bump` moves to the next step. Tasks without a `--workflow` flag have no steps — `relay bump` marks them `done` directly (the whole ticket is the only "step").

---

### Control plane and data plane

A ticket has two independent state machines.

**Control plane (status)** governs *whether* work happens — scheduling, prioritization, lifecycle. Same states everywhere.

| Status | Meaning |
|---|---|
| `draft` | Stub. Captured but not yet authored, or authored and waiting for approval. Not pickable for execution. |
| `active` | Someone is working on it. Workflow steps advance. |
| `paused` | Held. Workflow frozen at current step. Manual stop, or terminal error to revisit. |
| `done` | Closed. Success, abandoned, or failed — the actual outcome lives in the final log entry. |

Transitions are not constrained by the system in v1 — any status can move to any other. The convention is:

- `draft → active → done`
- `active → paused → active` (resume)
- `active → draft` (send back, needs rethinking)
- `active → done` (any terminal outcome — success, cancel, fail)

The default starting status comes from the top-level `default_status` field in `relay.toml` (defaults to `draft` if absent).

**Data plane (workflow step)** governs *what* work happens — the sequence of steps to complete the task. Per-task, frozen from the workflow definition at creation time. Step only advances when status is `active`. Pausing freezes the step. Sending back to `draft` does not reset the step.

---

### Task directory and the blackboard

**Tasks are directories, not files.** Each task lives in `relay-os/tasks/<slug>/` and contains:

```
fix-retry-logic/
  ticket.md             ← assignee, status, workflow step, description, context
  log.md                ← append-only structured log (written by CLI commands only)
  blackboard.md         ← shared workspace for human and agent
  task.lock             ← serializes concurrent access to all task files
```

**Single lock.** `task.lock` serializes writes to all files in the task directory. Under the one-task-one-worker constraint, a separate lock per file is unnecessary complexity.

**One task, one worker.** A task has exactly one assignee at a time — one human or one agent. Multiple workers never write to the same task concurrently. This is a deliberate v1 constraint for small teams (2-5 people). It means the lock file doesn't need to handle contention beyond accidental overlap (e.g., a human and an agent both running a CLI command on the same task at the same moment).

**Locks are local-only.** Lock files use file existence on the local filesystem. They serialize concurrent access on a single machine — they do not provide distributed locking across machines. This is sufficient under the one-task-one-worker constraint: if Marc's agent is working on task 003, Pierre's agent is not. Git merge conflicts on lock files are not expected in normal operation. If they occur, delete the lock and re-acquire — the dream/drift validation script covers stale lock detection.

**log.md** is append-only and structured. Written exclusively by CLI commands as a side effect — `relay launch`, `relay bump`, `relay panic`, and `relay create` all append to `log.md` when they execute. Agents and humans do not write to `log.md` directly. If agents need to record unstructured observations, they write to the blackboard. Format:

```
2025-01-14 10:32 [agent:claude1] advanced to step 2 (pr)
2025-01-14 11:01 [human:marc] approved
2025-01-14 11:04 [agent:claude1] started merge
```

#### The blackboard

The blackboard pattern originates in AI research (Hearsay-II, CMU, 1970s) for problems where multiple independent specialist processes need to cooperate without direct coupling. The idea: all processes share a mutable workspace. One writes a partial result; another reads it and builds on it; a third sees the combined state and fires. Coordination is emergent — no process talks directly to another.

Relay applies this pattern per task. `blackboard.md` is the shared workspace for the task. Any entity — human or agent — can write to it at any time (serialized via `task.lock`). There is no message passing between human and agent; they communicate through the board.

**blackboard.md** is unstructured by design. `relay create` scaffolds it as a near-empty file; the agent organizes it however fits the task — invent headings that make sense, or write flat. The base prompt teaches the agent what's worth capturing (plan, findings, decisions with reasons, blockers) without prescribing a section layout. Earlier drafts shipped a fixed Plan/Findings/Decisions/Blockers/Notes skeleton; it cost more in agent confusion than it bought in selective-load efficiency.

The blackboard is a workspace for live state — not a copy of the task's context. Domain knowledge and task-specific context live in the ticket (frontmatter context refs + inline body) and get composed into the prompt at launch time by `relay launch`. The blackboard captures what's happened *during* work: plans, findings, decisions, blockers. This avoids duplication between the blackboard and the composed prompt.

The default template:

```markdown
# Blackboard — {{task.id}} {{task.title}}

> Generated by relay at task creation.
> All sections are open to human and agent writes.
> Agents: read selectively by section heading — only load what your current step needs.

---

## Plan
<!-- Current working plan. Agent updates as it goes. Human can revise. -->
<!-- This is live — reflects current intent, not history. -->
<!-- When plan changes significantly, note what changed and why. Git history preserves the full trail. -->

---

## Notes
<!-- Free space. Drop anything here — questions, observations, links, half-formed thoughts. -->

---

## Findings
<!-- Agent: write discovered facts, intermediate results, research outputs here. -->
<!-- Human: read this to understand what the agent has learned. -->

---

## Blockers
<!-- Anything stalling progress. Human or agent can write. -->
<!-- The dream/drift validation script will flag tasks with open blockers and no recent log activity. -->

---

## Decisions
<!-- Rationale for choices made. Survives across runs — an agent relaunching reads this first. -->
<!-- Format: [date] [actor] decision + reason -->
```

**No separate archive file.** Git history is the archive. When the Plan section is updated, `git log` shows what was there before. This removes a file and a convention that agents would likely forget to follow.

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
| `status` | string | Control plane. One of: draft, active, paused, done. |
| `mode` | string | `interactive`, `auto`, or `script`. Default: `interactive`. Controls how `relay launch` starts work. `interactive`: human-attended session — agent starts with composed context, human present in terminal. `auto`: autonomous execution — agent receives composed context as one-shot prompt, runs without human input. `script`: direct execution — no agent spawned, script runs with secrets injected as env vars. |
| `owner` | string | Human accountable. Stable over the task's life. |
| `human` | string | Human worker on this ticket. Resolved from a workflow step's `assignee: human` token on bump. |
| `agent` | string | Agent (LLM coder) on this ticket. Resolved from a workflow step's `assignee: agent` token on bump. |
| `assignee` | string | Who's currently doing the work. Human name or agent nickname. Rewritten by `relay bump` when the next workflow step declares an `assignee:` role token; otherwise stable across bumps. |
| `watchers` | list | Additional people noted on the task. Owner and assignee auto-watch implicitly. (No-op for Slack: posts are plain-text broadcast at small team sizes.) |
| `workflow` | object | Frozen snapshot of the workflow at creation. Contains `name` (string) and `steps` (list of {name, skill?, assignee?}). |
| `step` | string | Current position in frozen workflow. Format: `N (step-name)`. Present while a workflow-bound task is not done; removed when the task is marked `done`. |
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
human: marc
agent: claude1
workflow:
  name: code/with-review
  steps:
    - name: implement
      skill: infra/testing-conventions
      assignee: agent
    - name: pr
      assignee: agent
    - name: approve
      skill: process/approve
      assignee: human
    - name: merge
      assignee: owner
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
status: draft
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

**Prompt composition.** `relay launch` builds a single composed prompt containing: global rules, repo context, ticket contexts, current workflow step skill, and the blackboard. This prompt is written to a temp file and passed to the agent via the appropriate CLI flag. The temp file is cleaned up after the session ends (interactive) or the command exits (auto). 

**Three launch modes.** Tasks declare their mode in ticket frontmatter (`mode: interactive`, `mode: auto`, or `mode: script`). Interactive (default): human-attended session, requiring stdin and stdout to both be terminals. Auto: autonomous execution — agent runs to completion without human input. Script: direct execution — no agent, just a script with secrets injected. See `relay launch` spec below.

**Secrets.** Credentials in `relay.local.toml`, injected as env vars at launch time by `relay launch`.

**Global rules.** `relay-os/rules.md` inlined in every composed task.

**Launch** Relay made to be used with a human or autonomously. In human mode, it will launch a terminal with the prompt loaded already.

**Launch is the approval gesture.** A `draft` task flips to `active` automatically when `relay launch` runs against it — running the launch *is* the human saying "go." The transition is logged. Re-launching an already-`active` task is a no-op on status. Bootstrap-skill tickets (those carrying a top-level `skill:` ref) are exempt: the bootstrap skill leaves them at `draft` so the *next* launch on the real ticket is the approval. `paused` tasks are not launchable at all — flip them manually to `active` or `draft` first.



### Crash recovery

**Crash recovery is manual in v1.** If an agent crashes mid-task (session dies, machine reboots, process killed), the human is responsible for cleanup:

1. Check the blackboard for last known state — the agent should have been writing findings and decisions as it worked.
2. Check for stale locks — clear if the agent is no longer running.
3. Relaunch with `relay launch` — the composed prompt includes the blackboard, so the new session picks up from the last written state.

The blackboard is the persistence layer between sessions. An agent that writes to the blackboard frequently (findings, plan updates, decisions) is recoverable. An agent that doesn't write is not. The relay base prompt includes instructions telling the agent to write to the blackboard after meaningful progress.

No automatic crash detection or restart in v1. The dream/drift validation script flags stale locks (suggesting a crash), but recovery is always human-initiated.

---

### Self-bootstrapping

The system improves itself using its own primitives. They are CLI commands executed as recurring tasks: they're regular tasks that use Relay's existing primitives.

#### Dream skill

Dream is Relay's bootstrap maintenance feature. It is a recurring orchestrator
for a small set of known shipped skills, not a project extension framework and
not one large cleanup script. The shipped skill lives at
`relay-os/skills/bootstrap/dream/SKILL.md`.

Dream runs only the skills explicitly listed in its own SKILL.md. Adding an
arbitrary file under `relay-os/skills/bootstrap/dream/tasks/` does not enable
it. There is no hidden registry, recursive discovery rule, daemon, database, or
cache.

This does not prevent user-space maintenance loops. A repo can define `rem`,
`ops/dream`, or any other ordinary skill/workflow/recurring task directly in
user space. That loop owns its own dispatch rules, state, naming, and
conventions. It is separate from bootstrap Dream rather than plugged into it.
Relay's shipped Dream stays explicit.

The current known skill set is:

| Skill | When to run | Result |
| --- | --- | --- |
| `bootstrap/dream/tasks/validate-drift` | Always. | Deterministic repo validation, safe file-presence repairs, and validation drift classification. |
| `retro/done-ticket` | When an existing done ticket lacks the `## Retro` blackboard marker for `skill: retro/done-ticket` / `status: processed` and no open PR is adding that marker. | PR-required knowledge extraction; marks the source task blackboard so Dream can clean it later. |
| `bootstrap/dream/tasks/dev/stale-branches` | When the repo is a git code repo and branch cleanup evidence is useful. | Proposal-only branch cleanup evidence. |

Every known Dream skill is an ordinary SKILL.md. Standard frontmatter stays
small: `name`, `description`, and optional `script` for executable skills. The
body includes a `## Known Skill Contract` section:

```markdown
## Known Skill Contract

- Purpose: <what maintenance question this skill answers>
- Runs: <exact command, manual instructions, or script entry point>
- Inputs: <files, commands, APIs, or task state the skill may read>
- May change: <none | exact files/refs the skill may edit>
- Action: <report-only | proposal-only | pr-required | direct-fix>
- Idempotency: <marker or proof that a unit was already handled>
- Stop and ask: <conditions that require human review before continuing>
- Output: <blackboard section, PR link, created ticket, or no-op result>
```

Action values are part of the contract:

- `report-only` reads state and writes a result to the Dream run blackboard.
- `proposal-only` writes evidence and proposed commands/edits, but does not
  mutate the repo or external systems.
- `pr-required` makes durable file changes only on a branch and opens a PR.
- `direct-fix` may make only the narrow deterministic change named in
  `May change`.

Destructive behavior is never implicit. Deleting task directories, deleting
git refs, removing locks, changing lifecycle state, or touching secrets
requires exact evidence and human review by default. A skill may declare direct
destructive behavior only when the rule is deterministic, narrow, and named in
`May change`; otherwise it uses `proposal-only` or `pr-required`.

Done-ticket Retro uses the source task blackboard as its idempotency marker.
Retro appends or updates exactly one section:

```markdown
## Retro

status: processed
skill: retro/done-ticket
result: <knowledge-pr | no-new-durable-knowledge>
title: <PR title>
```

For an existing `status: done` task, absence of that marker means Retro has
not processed the task. Presence of the marker means Dream must not run Retro
again and may delete the task when the cleanup gate is satisfied. Before
launching Retro for an unmarked done ticket, Dream checks open PRs; a PR whose
diff adds the same marker to `relay-os/tasks/<slug>/blackboard.md` counts as
in flight. If the task directory is already gone, it is not a Retro candidate;
git history for the deleted blackboard remains the audit trail.

Each known skill writes its own `## Dream Skill: <name>` blackboard section. At the
end of the run, the orchestrator appends one `## Dream Run Summary` section
with a skill result table (`no-op`, `reported`, `proposed`, `direct-fixed`,
`pr-opened`, or `human-needed`), knowledge-gap proposal counts, and any human
review gates. Slack gets one short summary line for the run.

After dispatching known skills, Dream still performs the higher-judgment scan:

- Context gaps: tickets that reference domain knowledge with no matching
  context, or repeated patterns not captured anywhere.
- Skill gaps: workflow steps with no skill, or blackboards showing repeated
  agent struggle.
- Workflow gaps: groups of tickets that follow the same ad-hoc sequence with
  no formalized workflow.
- Stale content: contexts or skills that contradict recent blackboards.

Those findings are proposals written to the blackboard. Each proposal is
concrete - "create context `infra/retry-patterns` covering: ..." - not a vague
recommendation. A human reviews and accepts or rejects.

Intended usage: a recurring task (`mode: auto`, scheduled weekly or ad-hoc)
assigned to an agent. Standard `relay launch`.

#### Create skill

A skill (`relay-os/skills/bootstrap/ticket`) is the authoring entry point for new tasks. `relay create` is a dumb scaffolder — `relay create "<title>"` lays down a task directory with `status: draft` and auto-launches this skill against it. The judgment lives in the skill.

When a human runs `relay create "<title>"` (or says "make me a ticket for X" inside an existing session), the skill:

1. Interviews the human until the work is framed (one question at a time).
2. Scans existing workflows, contexts, and skills to find what fits.
3. Edits the freshly-scaffolded `ticket.md` frontmatter to fill in workflow, contexts, assignee, watchers, mode.
4. Edits the `## Description` body with what to do and why.
5. Notes the rationale in the blackboard's Notes section.
6. Stops. Status stays at `draft` until the human approves and runs `relay launch`. The skill never launches the task itself.

If nothing in the inventory fits, the skill flags the gap on the blackboard for the dream skill to act on later — it never invents a workflow or context that doesn't exist.

#### Bootstrap tickets

Skills are knowledge, not entry points. To make a skill *runnable* without
remembering the prompt by heart, Relay ships persistent shim tickets under
`relay-os/bootstrap/<name>/`. Each one is a stateless launch target:

- Frontmatter pins `skill: bootstrap/<name>`. No `status`, no workflow, no
  step. The launcher composes the skill into the prompt at run time.
- `relay launch bootstrap/<name>` runs without flipping status to
  `active` and without acquiring `task.lock`. Concurrent launches by
  different humans are fine — the ticket is a re-entry point, not a unit of
  work.
- `relay launch bootstrap/<name> "title"` is a factory shorthand: scaffold
  a new task seeded from the shim's frontmatter (mode, assignee, skill),
  status=draft, then launch the agent on the new task to fill in the rest.
- The ticket directory accumulates `log.md` over time (a record of who
  invoked the shim and when), and may grow `blackboard.md` if the skill
  writes notes there. It does not participate in `relay status`.

`bootstrap/ticket` is the canonical example: it's how a fresh `relay-os/`
gets a "type one command and start authoring tasks" entry point. Future
shims (`bootstrap/dream`, etc.) follow the same shape.

#### Why this matters

These systems are very hard to bootstrap. By having agents do the initial work and maintain it, we ease the pain AND we follow our principle to keep everyting legible and open.

---

### Cron runner

Recurring tasks need a scheduler. Relay doesn't own the scheduler — the OS does. Relay provides the entry point.

`relay-os/scripts/cron.sh` is a script the user's system cron calls on a schedule. It:

1. Acquires a pidfile lock (`/tmp/relay-cron.pid`) — if another instance is already running, exit immediately. At most one cron run at a time.
2. Runs `relay recurring check` — scans recurring templates in `relay-os/recurring/`, creates any due tasks.
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

**Foreground and background.** The CLI has a foreground (commands humans reach for daily) and a background (commands agents call, taught by the system prompt). Background commands are fully exposed — a human debugging a stuck task can call `relay bump` or `relay panic` manually, see the same output, trigger the same side effects. Nothing is hidden; it's just layered. You learn the foreground first, discover the background when you need it.

### Commands

**Foreground** — what humans call:

| Command | What it does |
|---|---|
| `relay create "<title>"` | Default alias for `relay launch bootstrap/ticket "<title>"` — scaffolds a `draft` ticket and runs the bootstrap skill on it to interview the human and fill in workflow / contexts / description. See [Aliases](#aliases). For scripted scaffolding, call `scaffold_task()` in `relay.scaffold`. |
| `relay recurring check` | Scan recurring templates and scaffold any due tasks. |
| `relay launch` | Compose prompt from all context, inject secrets, start work on a task. Handles all three modes: interactive, auto, and script. |
| `relay status` | Show all active tasks in this repo. One line per task: id, title, assignee, step, mode. |

**Background** — what agents call (taught by the relay base prompt):

| Command | What it does |
|---|---|
| `relay bump` | Advance task one workflow step. Logs, notifies Slack. On the last step (or on a workflow-less ticket), marks the task done. Optional `--message` piggy-backs an FYI onto the broadcast. |
| `relay automerge` | Walk active tickets; bump any whose blackboard `## Dev` PR has merged. Looks PRs up via `gh pr view`. Symlinked into `.git/hooks/post-merge` by `relay init`, and called opportunistically from `relay status` so the long tail still gets caught. |
| `relay panic` | Agent is stuck. Write blockers to blackboard, post a Slack message naming the task owner, stop. |
| `relay slack` | Post an informational (FYI) message to the Slack channel. Manual broadcast escape hatch — for FYIs that don't fit a state transition. |

### Who edits what

**Humans** edit files directly — reassign a task, adjust context refs, tweak a workflow, update skills. The dream/drift skill includes a validation script that checks repo consistency (stale locks, broken references, invalid state) as part of its recurring run.

**Agents** edit files directly — write to the blackboard, update frontmatter fields (contexts, blockers). Agents call background commands within their self-service boundary, as taught by the relay base prompt.

---

### `relay launch` — decided spec

`relay launch <task-id> [title] [--agent <nickname>]`

`<task-id>` is a positional argument: a task slug (full or any unique
prefix, git-short-SHA-style) or a `bootstrap/<name>` shim. The optional
`title` arg is the factory shorthand for bootstrap shims — see "bootstrap
shims" above.

#### Behavior

1. Resolve the current user from `relay.local.toml`.
2. Look up the task in `relay-os/tasks/` (the CLI always operates on the repo it's running inside).
3. Read the `assignee` field from the ticket. Resolve the agent nickname in the user's `[assignees]` config to the agent type. `--agent <nickname>` may override the launched agent for this invocation only; on normal tasks it does not rewrite the ticket's `assignee`, while bootstrap factory launches use it as the scaffolded task's assignee.
4. Verify the task's `status` is `draft` or `active`. Error if not.
5. Load secrets from `relay.local.toml` `[secrets]` section. Resolve `env:VAR_NAME` references to actual values. These will be exported as environment variables into the launched process.
6. **Compose the prompt.** Assemble in this order:
   - Relay base prompt (how to operate within Relay — see below)
   - Mode-specific prompt block (interactive vs. auto behavioral rules)
   - `relay-os/rules.md` (global rules)
   - `relay-os/context.md` (repo-wide context)
   - Contexts referenced in ticket frontmatter (inlined from `relay-os/contexts/`)
   - Inline context from ticket body (the `## Context` section)
   - Current workflow step skill (inlined from `relay-os/skills/` if the step has a `skill:` reference, otherwise the inline instruction from the workflow markdown)
   - Blackboard (`blackboard.md`) — full contents
7. Write composed prompt to a temp file: `/tmp/relay-<task-id>-<timestamp>.md`
8. Read the `mode` field from the ticket. Default: `interactive`.
9. Launch based on mode:
   - **Interactive:** `{cli} {interactive-flag} /tmp/relay-<task-id>.md` — opens an interactive session with composed context loaded. Human is present.
   - **Auto:** `{cli} {auto-flag} "$(cat /tmp/relay-<task-id>.md)"` — sends composed prompt, agent runs to completion. CLI waits for exit.
   - **Script:** No agent spawned. Reads the current workflow step's skill, finds the script, executes it directly with secrets injected as env vars. No prompt composition, no LLM token cost. Script mode is single-shot; it does not enter the agent-step loop.
10. Log each agent process launch: append to `log.md` — `"launched in {mode} mode"`. The session start itself doesn't post to Slack; the surrounding state changes (factory create, draft → active flip, bump, panic, slack, script failure) each post on their own — see "What posts and when" below.
11. For workflow-bound interactive/auto tasks, re-read the ticket after a clean agent exit. Continue in a fresh agent process only when all of these are true:
   - the task is still `active`;
   - the step advanced during the previous process;
   - the new current workflow step has a `skill:` reference;
   - the concrete ticket `assignee:` is unchanged from the just-finished step.

   Each continued step re-composes the prompt from disk, including the newly updated ticket and blackboard. Stop cleanly when the task is `done` or `paused`, the next step has no skill, the assignee changed, or the agent exited cleanly without advancing the step. Stop with the agent's exit code on non-zero exits; `relay panic` already releases the lock and posts its blocker.

#### Composition order

The order is deliberate — it follows specificity:

1. Relay base prompt (how to operate — same for every task)
2. Mode-specific prompt block (interactive vs. auto behavioral rules)
3. Global rules (broadest — apply to everything)
4. Repo context (apply to all tasks in this repo)
5. Contexts (domain knowledge — scoped to this task type)
6. Inline context (task-specific — one-off details for this exact task)
7. Workflow step skill (process knowledge — what to do right now)
8. Blackboard (live state — what's happened so far, decisions, findings)

Later content overrides earlier content when they conflict. The agent sees the most specific information last, which is where most LLMs place the highest weight. The base prompt comes first because it's structural — it defines how the agent interacts with the system, not what it does. It should never be overridden by task-specific content.

#### Multi-task per repo

`relay launch` takes one task target as a positional arg. It launches exactly one task per invocation. If you have two active tasks in the same repo, you launch them separately in separate terminal sessions.

#### Errors

| Scenario | Behavior |
|---|---|
| Task not found | Error. Show available tasks. |
| Assignee not found in current user's agents | Error. "Task 003 is assigned to `claude2`, which is not in your agent config." |
| Task status is not launchable | Error. "Task 003 is `paused`. Set to `active` (or `draft`) before launching." |
| Agent CLI binary not found | Error. "{cli} not found in PATH." |
| Missing context or skill reference | Error. List the missing references. Do not launch. |
| Mode is `script` but no script found in step's skill | Error. "Step `publish` has no script to execute." |

---

### `relay panic` — decided spec

`relay panic --task <task-id> --reason "<text>"`

#### Behavior

Writes a timestamped blocker line to the blackboard, posts to the Slack channel naming the task owner, stops the agent. This is the only escalation mechanism for autonomous agents.

Example:

```
relay panic --task 003 --reason "429 retry logic unclear, need decision on backoff ceiling"
```

Slack: `marc: 003 "Fix retry logic" — agent stuck: "429 retry logic unclear, need decision on backoff ceiling"`

`--reason` is required.

---

### `relay bump` — decided spec

`relay bump <task-id> [--message "<short FYI>"]`

A thin command for side effects. The agent calls this when it completes a workflow step. The intelligence about *when* to call it lives in the relay base prompt, not in the command. The task arg is positional; the command always advances by exactly one step (there is no "skip ahead" form).

#### Behavior

1. Read the task's current step from ticket frontmatter.
2. Validate: task status must be `active`. Error if not.
3. If the task has no workflow steps, set `status: done`, remove any stale `step` field, and release the lock.
4. If the current step was already the last one: set `status: done`, remove `step`, and release the lock.
5. Otherwise compute the next step (`current + 1`) and update the `step` field in ticket.md.
6. Append to `log.md` — `"advanced to step N (step-name)"` or `"task done"`. When `--message <text>` is set, append ` — <text>` to the log line.
7. Post to Slack: FYI — step transition or task completion. When `--message <text>` is set, append ` — <text>` to the broadcast.

#### Errors

| Scenario | Behavior |
|---|---|
| Task is not `active` | Error. "Task 003 is `paused`. Cannot advance." |
| Task has no workflow | Not an error — marks task `done` directly and notifies. |
| Already on last step | Not an error — marks task `done` and notifies. |

---

### Repo consistency checks

Repo validation (stale locks, broken references, invalid status values, stuck tasks) is handled by a deterministic validation script, not an LLM. `relay validate --fix` may apply only conservative file-presence repairs: create missing `blackboard.md` from the standard template and create missing `log.md` as an empty append-only file. It never rewrites existing files, reconstructs `ticket.md`, freezes workflows, deletes locks, or changes lifecycle/assignee state.

The Dream `validate-drift` skill runs the same validator surface, usually as `relay validate --json --fix`, classifies remaining issues into `direct-fix`, `pr-proposal`, or `human-needed`, writes a concise result to the Dream run blackboard, and can post a one-line Slack summary for the run. When a Dream run is already on a repair branch, the skill can also commit and push the files it repaired; that push path is intentionally outside plain `relay validate`. The broader Dream scan can then interpret remaining drift alongside knowledge gaps, stale content, and workflow patterns.

Checks include:

- Task directories have all required files (ticket.md, log.md, blackboard.md)
- Blackboard files stay under the prompt-bloat warning threshold
- Lock is not stale (held for unexpectedly long — likely a crashed agent)
- Tasks stuck in `active` status with no recent log activity
- Workflow step references point to skills that actually exist
- Context references in tickets point to contexts that actually exist
- Assignees in task files match known users in `relay.toml`
- Status values are valid (one of: draft, active, paused, done)

Stale locks are conservative by default. Validation can prove that a lock is
older than the configured threshold, but it cannot prove from age alone that no
live terminal or agent owns it. Dream reports stale locks as human-needed unless
a human verifies that the task is not currently running, then removes
`task.lock` or relaunches with `--force`.

---

## Relay base prompt

The relay base prompt is a system prompt injected at the top of every composed prompt by `relay launch`. It teaches the agent how to operate within Relay — not what to do (that comes from skills, contexts, and the ticket), but how to behave as a participant in the system.

This is the most important piece of the spec. When commands like `relay bump` were thinned to pure side-effect runners, the base prompt became the brain — it carries the logic about when to advance, when to panic, how to use the blackboard, and how to handle frontmatter.

### What the base prompt covers

1. **Identity** — you're an agent working on a ticket inside Relay.
2. **Files** — what ticket.md, blackboard.md, and log.md are for. Which you read, which you write, which you don't touch.
3. **Blackboard discipline** — write frequently (plan, findings, decisions, blockers). The blackboard is unstructured by design and is the crash recovery mechanism. An agent that writes to it is recoverable; one that doesn't is not.
4. **Step transitions** — do the work for your current step. When done, call `relay bump`. Do not go back. If a previous step needs rework, panic.
5. **Escalation** — call `relay panic` when stuck. Be specific about the reason. Write the blocker to the blackboard before panicking. After panicking, stop.
6. **FYIs** — `relay slack` posts a standalone FYI; `relay bump --message` piggy-backs an FYI onto a state-transition broadcast. Keep messages short. Do not use either for blockers.
7. **YAML discipline** — preserve existing fields, use exact syntax, don't invent formats.

### Mode-specific blocks

The base prompt has a section (same for every task) and a mode-specific block swapped in by `relay launch`:

**Interactive block:** You're working with a human. Ask when uncertain. Discuss tradeoffs. The human is here.

**Auto block:** You're alone. Either proceed (and note uncertainty on the blackboard) or panic. Do not write questions and wait — nobody is watching.

The `script` mode does not use the base prompt — no agent is spawned.

### Why this matters

Before the base prompt, agents needed to know Relay's conventions through their instruction file (CLAUDE.md, AGENTS.md) or through ad-hoc prompting. This was fragile — every agent type needed separate instructions, conventions drifted, and there was no guarantee the agent knew how to use the blackboard or when to escalate.

The base prompt standardizes this. Every agent, regardless of type, receives the same operating instructions at launch time. The instructions are version-controlled, editable, and visible — consistent with the "no magic, everything exposed" design principle.

### Prompt templates replaced

The earlier spec flagged "prompt templates for agent file editing" as a blocking dependency. The relay base prompt resolves this — it teaches YAML formatting rules, blackboard conventions, and file discipline directly in the system prompt. No separate template system needed.

### Location

The relay base prompt lives at `relay-os/prompt.md` (base) and `relay-os/prompt-interactive.md` / `relay-os/prompt-auto.md` (mode blocks). Version-controlled alongside skills, contexts, and workflows.

---

## Slack feed

**What:** A live activity feed in a shared Slack channel. Every state change across the company posts automatically. Plain text — no @mentions.

**Why:** Agents work asynchronously. Humans need to know when something needs their attention (review, approve, unblock) and what their agents have been doing. The Slack channel is the primary awareness layer — a scrollable timeline of everything happening across all the repos a team operates. Multiple repos can post into the same channel; that's the cross-surface view.

### Design principles

The assumption is to overshare. Every state-changing CLI command posts to Slack. No filtering, no agent decision-making about what's "worth" notifying. The channel is a complete feed. If it ever gets too noisy, that's a good problem — it means a lot is getting done, and we can dial back then.

The shared channel is deliberate: team-wide visibility and mutual accountability. Everyone sees what's moving. At small team sizes (≤3 people) everyone reads the channel anyway, so plain posts reach the right person without explicit @mentions. Re-introduce per-user mentions when team size makes "who needs to look at this" stop being obvious.

### What posts and when

| Event | Posts |
|---|---|
| `relay create` (factory-mode launch with title) | New draft ticket scaffolded |
| `relay recurring check` | One post per scaffolded task; one summary post when any templates failed to parse |
| `relay launch` (draft → active) | Ticket activated — work approved |
| `relay bump` | Task moved to next step (or completed on last step) |
| `relay panic` | Agent stuck, owner named in message |
| `relay slack` | Custom FYI message from agent or human (e.g. "opened PR #142", "reassigned to pierre") |
| `relay launch` (script mode failure) | Script exited non-zero |

Opening an interactive or auto session on an already-active ticket
does *not* post — that isn't a sync-relevant state change. Tickets are
assigned, collision risk is low, and the actual transitions
(creation, activation, bumps, panics, slack FYIs, script failures) each
broadcast on their own.

### Notification logic lives in the CLI

The agent calls `relay bump`, etc. as normal. The CLI decides what to post. Agents never reason about what's worth notifying — the commands themselves are the notification hooks.

### Delivery

Shared Slack channel via an incoming webhook. The URL itself lives in `$SLACK_WEBHOOK_URL` — each user (or each machine in a multi-machine setup) exports it locally. The webhook is channel-bound and is a bearer token; relay never commits it. Slack is required by default and a missing webhook crashes commands at use time, since silent FYI failures break the team's mental model. To opt out (solo / dev / CI), set `[slack].enabled = false` in `relay.local.toml`.

### Message format examples

```
marc's claude1 completed step 2 (pr) on 003 "Fix retry logic"

New task: 005 "LinkedIn post retry logic" assigned to marc (workflow: content/post)

marc's claude1: pushed branch, opened PR #142 (003)

003 "Fix retry logic" done ✓

marc: 003 "Fix retry logic" — agent stuck: "429 retry logic unclear"
```

Each repo's webhook can point at the same channel — the source repo isn't part of the message format, so if cross-surface disambiguation matters, include it in the channel name (`#admin-relay`, `#code-relay`) or in the slack app config rather than in every message.

---

## Error model

Every CLI command can fail. The spec describes happy paths — this section defines failure behavior.

**General principles:**

- **Fail loud, fail early.** CLI exits with a non-zero code and a human-readable error message. No silent failures. No partial state changes — if a multi-step command fails partway, it should either roll back or leave a clear trail of what completed and what didn't.
- **Agents see errors too.** When an agent calls `relay bump` or `relay panic` and it fails, the agent sees the stderr output. Error messages should be actionable enough that an agent can log the failure and flag it, or retry if appropriate.
- **Slack gets notified on failures that matter.** If `relay launch` fails with `mode: script` (script exits non-zero), or `relay bump` fails on an active task, post to the Slack feed so the human knows.

**Specific failure cases:**

| Scenario | Behavior |
|---|---|
| Lock can't be acquired (already held) | Error with holder identity and acquisition time. Agent/human decides whether to wait or force. `--force` flag to break stale locks. |
| `relay launch` with `mode: script` exits non-zero | Log the failure to log.md. Post to Slack. Task stays at current step. |
| `relay bump` on a non-active task | Error. Task must be `active` to advance. |
| `relay create` with missing context/skill references | Error. List the missing references. Do not create the task. |
| `relay create` outside a `relay-os/` tree | Error. The CLI requires a `relay-os/` somewhere in an ancestor directory. |
| `git push` rejected | Show the git error. Suggest `git pull --rebase` then retry. Do not auto-resolve. |

Note: `relay bump` on the last step is not an error — it marks the task `done` and notifies. See `relay bump` spec.

---

## V2 backlog

Items to evaluate after v1 is built and used. Not designed yet.

1. **Per-repo control plane workflows.** The universal status list (draft, active, paused, done) could become an editable state graph per repo — same workflow primitive as the data plane, but with branches and backward edges. Requires extending the workflow format to support non-linear graphs.
2. **Priority / ordering.** Skipped for v1. If 15+ active tasks in a repo makes it hard to know what to work on next, add then.
3. **Real Slack app.** Bot token with `chat:write` + `users:read` scopes for DMs instead of shared channel @mentions.
4. **Fully autonomous agent chains.** Agent-to-agent handoff: when agent A completes its step and the next step is assigned to agent B, auto-trigger `relay launch` for B. Requires lifting the `reassign`-to-agent restriction. Depends on v1 learnings about how often multi-agent chains actually occur.
5. **System-prompt-level injection for Codex/OpenCode.** Currently `interactive` and `auto` use the same subcommand for these tools because they lack `--system-prompt` flags. When these tools add them, update agent config to prefer system-level injection.
6. **`relay update-workflow`.** Re-snapshot a workflow definition into an in-flight ticket's frontmatter while preserving the current step position. Useful when workflow definitions change frequently during iteration. For v1, manually edit ticket frontmatter instead.

---

## Removed

**Multi-project federation** — removed. Earlier drafts of the spec had `[projects.<name>]` blocks in `relay.toml`, a `[paths]` section in `relay.local.toml` mapping each project name to a separate filesystem location, a `--project` flag on every CLI command, and `project/id-slug` task references. In practice every repo only ever declared one project — the federation primitive was overhead for a 1-of-1 dimension. The new model: **the repo IS the project.** A team running multiple operational surfaces uses multiple repos, one `relay-os/` per repo, and gets a unified view via Slack (every repo's webhook can post into the same channel) rather than via a CLI federation layer. `default_status` moves from per-project to a top-level field in `relay.toml`.

**`relay inbox`** — removed. The Slack feed is the notification layer. No local inbox command.

**`run` field on workflow steps** — removed. Workflows don't define who does the work. The `assignee` field on the ticket controls that. Slack posts trigger on assignee changes (when the new assignee is a human), replacing the old `run: human` trigger.

**`created` field in ticket frontmatter** — removed. The first log entry is the source of truth for when the ticket was created.

**`recurring` status** — removed. Recurring tasks are handled by templates in `relay-os/recurring/` with cron schedules, not by a task status. A completed recurring task is `done`. The template creates a fresh task on the next cycle. Scheduling is a concern separate from task lifecycle.

**`skills` in ticket frontmatter** — removed. Skills attach to workflow steps, not tickets. Contexts attach to tickets. This gives a functional distinction: skills = process knowledge flowing through workflows, contexts = domain knowledge scoped to a task.

**`relay reassign`** — removed. Human-to-human reassignment is done by editing the `assignee` field in ticket frontmatter directly. Agent escalation is handled by `relay panic`.

**`relay done`** — absorbed into `relay bump`. Bumping past the final step sets status to `done` and notifies.

**`relay log`** — removed from CLI. Log entries are written by CLI commands as internal side effects. Agents and humans do not write to `log.md` directly — use the blackboard for unstructured observations.

**`relay status`** — moved to convenience command. Shows one-line-per-task summary for the current repo.

**`relay run`** — removed. Absorbed into `relay launch`. Script execution is handled by `mode: script` — `relay launch` reads the step's skill, finds the script, runs it directly with secrets injected as env vars. No separate command needed; the agent calls scripts natively during interactive/auto sessions.

**`relay recurring`** — kept as a real subcommand. `relay recurring check` scans templates and scaffolds any due tasks; the cron job calls it directly. (Earlier draft absorbed it into `relay create --check-recurring`; once `relay create` became a thin alias, hanging the recurring flag on it stopped making sense.)

**`relay check`** — removed as standalone command. Repo validation (stale locks, broken references, invalid state) is now a deterministic script inside the dream/drift skill. The skill runs the script, the agent interprets the output.

**`relay sync`** — removed. Was a ghost reference in the error model with no spec. Git push/pull is manual.

**`relay advance`** — renamed to `relay bump`. Thinned to a side-effect command (update step field, log, notify Slack). The intelligence about when to advance lives in the relay base prompt, not the command.

---

## Still underspecified — needs design before or during v1 build

### Blocking — must resolve before building

#### `relay create`

No detailed behavior spec. Now also absorbs recurring template checking. Open questions:

- Which frontmatter fields are set automatically vs. passed as CLI args?
- How does create-with-suggestions integrate? Is it a post-create hook? A flag?
- Handling of duplicate context references.
- Skills from workflow steps are not composed at creation time — they are loaded at launch time for the current step. Confirmed, but the boundary needs to be explicit in the spec.
- Recurring integration: how does `relay recurring check` detect "already created for this period" — naming convention on created task, or `last_run` field updated in the template?
- What "due" means for different schedule frequencies (daily, weekly, monthly).

#### ~~Task ID generation~~ — resolved

Slug-only. Each task lives at `relay-os/tasks/<slug>/`, where `<slug>` is derived from the title (lowercase, hyphens, truncated to 50 chars). There is no numeric ID and no `counter` file — the directory name is the canonical reference. If a slug collides with an existing task, the new one gets `-2`, `-3`, … appended. Tasks resolve by exact slug or any unique prefix (git-short-SHA-style); ambiguous prefixes error and list the matches. Slugs appear in branch names (`relay/fix-retry-logic`), Slack messages, and cross-references. The earlier counter-backed `NNN-slug` design was dropped because the counter file fights git: parallel branches both mint the same next ID, and the merge has to be hand-resolved. Slugs sidestep that — collision detection happens against the actual filesystem state at create time.

#### `relay create` CLI interface

The command's arguments are not defined. Open questions:

- What's the invocation? `relay create --workflow code/with-review --title "Fix retry logic"`? Interactive prompts? A mix?
- Which arguments are required vs. optional?
- The create-with-suggestions skill implies a conversational post-create flow, but the base command needs a defined argument interface before that can layer on top.

#### Lock lifecycle

Lock format is defined (holder + acquired timestamp, file-existence based). The acquire/release lifecycle is not. Open questions:

- When is the lock acquired? By `relay launch`? By the first CLI command the agent calls?
- When is it released? On process exit? On `relay bump` to `done`? On `relay panic`?
- What happens on Ctrl+C in interactive mode — is release tied to a signal handler?
- Does `mode: script` acquire a lock?
- Stale lock detection threshold — how long before the dream/drift script considers a lock stale?

#### Interactive and auto prompt blocks

The base prompt (`relay-os/prompt.md`) and the mode-specific blocks (`prompt-interactive.md` and `prompt-auto.md`) are written. They're version-controlled markdown alongside skills and contexts; refine as we learn what agents reliably ignore vs. follow.

### Should resolve — but won't block initial build

#### `relay panic`

Described briefly but not at the level of `relay launch`. Missing:

- Full error table (what if task has no owner? what if agent is in interactive mode? what if the task isn't active?).
- Exact format of the blocker line written to the blackboard.
- Does panic change the task status? (e.g. to `paused`?)

#### Step transitions with assignee changes

When `relay bump` advances to a step where a different person should take over (e.g. implement → approve), what happens? Does the system prompt teach the agent to reassign? Does `relay bump` handle it? This is especially important for the approve step pattern.

#### Task lifecycle transitions

- What happens to the workflow step when status moves to `paused` then back to `active`? (Expected: resumes at same step. Confirm.)
- What happens to the workflow step when status moves to `draft`? (Expected: preserves step. Confirm.)
- Should invalid transitions be rejected or just warned about by the dream/drift validation script?

#### Workflow-less tasks

- Tasks without a `workflow` field use simple status transitions (no steps).
- Interaction with `relay bump` (error? no-op?).
- How do they appear in `relay status`?

#### `step` field management

- If someone manually edits the step field, what happens? Is the ticket the source of truth even for manual edits?
- Format `N (step-name)` — is N 1-indexed?

#### `relay status` — detailed behavior

Listed as a foreground command but has no spec beyond "show all active tasks in this repo." Open questions:

- What does the output look like? Columns, formatting?
- Filters: by assignee, by status?
- Sorting: by recency, by status?
- Does it show only `active` tasks, or all non-done tasks?

#### `relay slack` — detailed behavior

Listed as a background command but has no spec beyond the base prompt description. Open questions:

- Does it require `--task`? (Likely yes — agent is always working on a task.)
- Does the message format include task context automatically, or does it post the raw string?
- Is there a character limit?

#### Script mode execution path

`relay launch` with `mode: script` says "finds the script, executes it directly." The error table covers "no script found" but the happy path is thin. Open questions:

- How does it find the script — first executable in the skill directory? A `script` field in the skill frontmatter?
- What's the working directory — the repo root? The task directory?
- What if the step has inline instructions instead of a `skill:` reference — is that an error for script mode?
- Exit code handling beyond non-zero = failure?

#### Task resolution — resolved

`--task` (and the positional arg on `relay launch`) accepts an exact slug or any unique prefix. Exact matches win even when the arg is also a prefix of a longer slug. Ambiguous prefixes error with all matches listed (`Ambiguous task ref 'fix-': matches fix-retry-logic, fix-timeout-handling. Use a longer prefix to disambiguate.`).

Open: should `relay bump`, `relay panic`, `relay slack` infer the task from the current working directory (e.g. when invoked from inside `relay-os/tasks/<slug>/`) instead of always requiring `--task`?

### Can defer — resolve during or after 3-month internal use

#### Archival / cleanup of done tasks

- Do done tasks accumulate in `relay-os/tasks/` forever?
- Is there a prune or archive command? Auto-cleanup after N days?
- Will know what's needed after 3 months of use.

#### `relay init`

- Setup command. Not spec'd in detail beyond listing.
- Manual repo setup works for v1.

#### Task dependencies

- No structured way to say "task B blocked by task A."
- Blocker lines on the blackboard are freeform.
- Likely sufficient for v1 at this team size.

#### Context/skill staleness

- No mechanism to flag stale skills or contexts beyond the dream skill's periodic scan.
- Dream skill likely handles this. Revisit if it doesn't.

#### Git merge conflicts

Git is the sync layer. The one-task-one-worker constraint means two people rarely touch the same task files. Conflicts are most likely on `relay.toml` (config edits) or rare human-edits-while-agent-pushes cases. Slug-only task names (no shared counter) eliminate the ID-collision conflict entirely — two parallel `relay create` runs only collide if they pick the exact same slug, in which case the second gets a `-2` suffix. Manually resolved for v1.

#### Prompt size / token limits

No full composed-prompt token budgeting yet. A task with multiple contexts, a rich skill, a long blackboard, and a detailed ticket body could exceed limits. Relay warns on the most obvious controllable case — `blackboard.md` larger than 32 KiB — but broader prompt measurement and mitigation remain future work.

#### Blackboard growth

Over a long-running task with many relaunches, the blackboard grows unbounded. Findings and decisions accumulate across sessions. Eventually competes for context window space. `relay launch` and repo validation warn once `blackboard.md` crosses 32 KiB, but there is no automatic pruning or summarization strategy. May not matter for v1 task durations — revisit if tasks routinely span 10+ sessions.

#### Temp file cleanup

Composed prompt is written to `/tmp/relay-<task-id>-<timestamp>.md`. Spec says "cleaned up after the session ends (interactive) or the command exits (auto)." Crashes leave orphans. Probably harmless (`/tmp` is ephemeral on most systems) but unaddressed.
