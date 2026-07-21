# Concepts

Coga is a markdown-first, git-backed operating system for running work with
agents. Everything an agent operates on is a file under `coga/`. There is no
database, no daemon, no in-memory state. This page explains the pieces and how
they fit; the [command reference](reference.md) covers the verbs that act on
them.

The design has one root — *don't don't think; think better* — and everything
below is a consequence of it. The canonical statement lives in the contexts your
agents actually load: [`coga/contexts/coga/principles/SKILL.md`](../coga/contexts/coga/principles/SKILL.md)
(the non-negotiables) and `coga/contexts/coga/architecture/SKILL.md` (the
system model). This page is the human-readable tour of the same ideas.

## Tickets

A **ticket** is one durable unit of work. It's a markdown file with three parts:

```
---
slug: add-a-health-check-endpoint
title: Add a health-check endpoint
status: in_progress
owner: marc
agent: claude
workflow: { name: code/with-review, steps: [...] }
step: 1 (implement)
contexts: [service/http]
---

## Description
...the body: what to do, and any task-specific ## Context...

<!-- coga:blackboard -->

## Dev
branch: health-check
...the free-form shared workspace...
```

- **Frontmatter** — canonical fields (`status`, `owner`, `agent`, `workflow`,
  `step`, `contexts`, and a few more). CLI commands own the lifecycle fields; you
  hand-edit only `contexts` and the body. A repo can declare extra fields (say, a
  `priority` tier) in `coga.toml`.
- **Body** — the source of truth for *what the task is*: `## Description` and an
  optional inline `## Context`. This is yours to write.
- **Blackboard** — everything after the `<!-- coga:blackboard -->` fence. See
  below.

Tickets live under `coga/tasks/`. A **task is a directory containing a
`ticket.md`, at any depth** — `tasks/health-check/` or
`tasks/marketing/social/relaunch/`. Those sub-directories are just plain
directories you organize with `mkdir`, `mv`, and `rm`; Coga reads the tree but
never invents machinery for it. A self-contained task can also be a bare
`tasks/<slug>.md` file; it grows into a directory only when it needs companions
(a script, attachments). You refer to a task by its path under `tasks/` — its
leaf name at the top level, otherwise the relative path.

**Why files and not a database?** Because you can only think well about what you
can see. A ticket is legible to a human and an agent alike, it diffs cleanly, and
it survives the process that created it. Work that isn't a ticket — a loose
branch, a one-off command, an agent action that leaves no trace — is work you
can't hand off, resume, or later correct.

## The blackboard

The **blackboard** is the free-form region at the bottom of every ticket. It's
the shared working memory between a human and an agent, and between one agent
session and the next. Sessions are stateless — when a REPL is torn down, the
blackboard is what's left. So the loop for every agent is: **read the blackboard
first, do the work while writing findings and decisions back to it, then bump.**
An agent that writes to it often is recoverable; one that doesn't is not.

Keep it small. The blackboard is composed into every launch prompt, so it's
working memory, not an archive. Durable history goes somewhere else:

## The log

The append-only audit trail is **not** in the ticket. It lives in one
repo-global file, `coga/log.md`, each line tagged with its task. CLI commands
(`create`, `bump`, `mark`, `launch`, `block`, and the rest) are its only
writers — you never hand-edit it. Because it lives outside every task and is
never composed into a prompt, it can grow without bound.

That's a deliberate division of labor: **working state the next run must read
goes on the blackboard (small, composed); durable history goes in the log
(unbounded, never composed).**

## Contexts and skills

Both are SKILL.md files — frontmatter (`name`, `description`) plus a markdown
body. The difference is what kind of knowledge they carry:

- **Contexts** are *domain knowledge* — what's true about your world. "How our
  billing flow works," "the house style for API docs." Attached to a ticket via
  its `contexts:` frontmatter list, and composed into that ticket's prompts.
- **Skills** are *process knowledge* — how to do a thing. Usually attached to a
  **workflow step**, so the right how-to loads exactly when its step runs. A
  skill that applies to the whole ticket regardless of step can instead go in
  the ticket's `skills:` frontmatter list.

Both resolve **local-first**: a file under `coga/contexts/` or `coga/skills/`
overrides a bundled one of the same name that ships with the package. To change
a shipped context or skill, copy it to the matching path and edit — no plugin
API, no fork.

## Workflows and steps

A **workflow** is an ordered list of steps. `code/with-review`, for example, is
`implement → peer-review → open-pr → review`. Each step can name the skills it
needs and an **assignee** role — `agent`, `other-agent`, `human`, or `owner`.
When a step advances, the role resolves against the ticket's people/agent fields:
`other-agent` flips to the peer agent, which is how a change written by Claude
gets reviewed by Codex (and vice versa).

The critical property: a workflow is **frozen into the ticket** when it's
attached — at creation if you pass `--workflow`, otherwise at activation for a
draft that gains its workflow later (a hand-added `workflow:` or the guided
`coga ticket` interview). Once frozen, editing `coga/workflows/foo.md` changes
future tickets, never one already in flight. Workflows resolve local-first like
everything else — a repo's own `coga/workflows/` override the bundled ones
(`code/*`, `docs/with-review`, and friends).

A ticket doesn't need a workflow to exist as a draft, but it needs one to be
activated — a launched ticket that no `coga bump` could ever advance is a stuck
task, and Coga refuses to create that situation at activation time.

## The two state machines

Every ticket tracks two independent things, and different commands own each:

- **Status — *whether* work happens.** `draft → active → in_progress → done`,
  plus `paused` and `blocked`. `coga mark` owns the draft/active/paused/done
  transitions; `coga block` and `coga unblock` own `blocked`; `coga launch`
  flips `active → in_progress` when it spawns the agent (and activates a draft
  inline first).
- **Step — *where* in the workflow.** Format `N (step-name)`. Owned entirely by
  `coga bump`, and only moves while status is `in_progress`. A bare `coga bump`
  advances one step; a human (outside a supervised launch) can rewind with
  `--to` or `--backward`.

Keeping them separate is what lets you pause a task without losing its place, or
resume a blocked task at the exact step it stopped on. Tickets with no workflow
have no steps and move through statuses directly.

There's no lock file. **Status is the signal** that someone is (or isn't)
working on a task. If two people launch the same ticket, the divergence is
visible and recoverable in Git — which Coga prefers to the stale-lock, `--force`,
orphan-cleanup tax of a real mutex.

## Agents and scripts

Whether a launch runs a **script** or spawns an **agent** is deduced per launch,
not set by a field:

- If the current step's single skill declares a `script:`, or the ticket itself
  owns a `script:`, the launch runs that code directly — no prompt, no agent, no
  TTY. This is the right shape for deterministic, recurring, or CI work.
- Otherwise, the launch composes a prompt and spawns the assignee's agent CLI in
  a live REPL.

One workflow can freely mix the two: an `implement` step spawns an agent, a
later `publish` step runs a script. A script step advances only when its script
exits zero — completion is gated by an exit code, not an agent's say-so.

The two agent CLIs — **Claude Code** and **Codex** — are interchangeable.
They're configured in `coga.toml` under `[agents.*]`, and the `other-agent`
rotation is what drives peer review across vendors. No single model vendor owns
your workflow.

## Composition: how a prompt is built

`coga launch` builds one prompt, fresh, every time, by stacking layers in order:

1. Base prompt + agent-mode instructions (shipped with the package).
2. This repo's context (`coga/context.md`).
3. The ticket's attached `contexts:`.
4. The ticket body's inline `## Context`.
5. The current step's skill (and any ticket-level skills).
6. The blackboard.
7. The task description (the body's `## Description`).

That's the whole input — there's no follow-up loading. Two consequences worth
internalizing:

- **The prompt is a pure function of the files on disk now.** Nothing is carried
  over from a previous session. That's precisely why an edit between runs takes
  effect completely and inspectably: fix the file, relaunch, done.
- **The log is deliberately never a layer.** Only the blackboard (layer 6)
  carries state forward, which is why it must stay small and the log can grow
  forever.

If a prompt gets bloated, `coga launch <task> --prompt-report` shows which layer
to trim.

## Fail loud

Coga would rather crash than hand you a confident wrong answer. A missing context
or skill raises instead of being silently dropped from the prompt. `coga
validate` errors on broken references. A failed notification surfaces rather than
returning success. Read-only commands (`status`, `show`, `validate`) never mutate
state or hit the network as a side effect of reading. The worst failure is an
agent producing wrong output because something silently didn't load — so Coga
checks.

## Memory compounds through review

Better thinking has to *accumulate* without becoming opaque automatic memory that
*replaces* thinking. So knowledge compounds through human-reviewed diffs, never
learned weights or a hidden store:

- The **blackboard** is a task's working memory.
- **Contexts** are long-term memory, merged by hand.
- The **correction loop** is you: agent gets it wrong → you edit the context →
  commit → next run is fixed.
- **[Dream](operations.md#dream-generic-ticket-cleanup)** is the agent instance
  of that loop: a recurring pass that reads tickets and blackboards, spots where
  a context drifted from reality, and opens a **proposal PR**. It proposes; you
  dispose. Nothing edits your operating rules on `main` without your merge.

## Where this is written down

You never have to trust this page over the system. Every claim here traces to a
file you can open:

- The non-negotiables: [`coga/contexts/coga/principles/SKILL.md`](../coga/contexts/coga/principles/SKILL.md)
- The system model: `coga/contexts/coga/architecture/SKILL.md`
- The essay behind both: [vision.md](vision.md)
