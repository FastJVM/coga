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

Both resolve **local-first**: a file under the repo's contexts directory or
`coga/skills/` overrides a bundled one of the same name that ships with the
package. To change a shipped context or skill, copy it to the matching path and
edit — no plugin API, no fork.

Contexts live at `coga/contexts/` by default, but because they are the one
primitive humans hand-edit as prose, a repo can move them somewhere its writers
actually work:

```toml
# coga.toml
[layout]
contexts = "docs/contexts"
```

The path is relative to your Git checkout root — the same value means the same
place whether `coga.toml` sits in a nested `coga/` or at the repo root — and
must name a child directory inside the checkout, since contexts are git-backed
state like everything else. The directory needs at least one tracked or
unignored file (`.gitkeep` is enough when it is intentionally empty), so a fresh
clone can reproduce it. Set it and the whole system follows: composition,
validation, ref resolution, and the git sync that commits both the new files
and tracked removals from the former contexts root. A scaffolded config with
the key set also makes `coga init` create and commit its initial local contexts
at that checkout-root-relative destination; `coga uninstall` lists and removes
that directory as part of the Coga footprint. A missing, empty, ignored,
symlinked, checkout-wide, coga-root-containing, Git-administrative,
nested-checkout, or pathspec-like value fails at config load; so does a real
context `SKILL.md` hidden by an ignore rule. These checks prevent Coga from
quietly dropping composed contexts or widening the state sweep. Skills have no
such knob; they are process knowledge for agents, not prose for humans.

## Workflows and steps

A **workflow** is an ordered list of steps. `code/with-review`, for example, is
`implement → peer-review → open-pr → review`. Each step can name the skills it
needs and an **assignee** role — `agent`, `other-agent`, `human`, or `owner`.
When a step advances, the role resolves against the ticket's people/agent fields:
`other-agent` uses the ticket agent's configured `peer` when present, otherwise
it infers the only other configured type. That keeps two-agent repos automatic;
with three or more types, each agent that uses `other-agent` declares its own
one-directional peer or validation fails loud instead of guessing.

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

- **Status — *whether* work happens.** `draft`, `active`, `in_progress`,
  `paused`, and `blocked`, plus the distinct terminal outcomes `done` and
  `canceled`. `coga mark` owns active/paused/done/canceled transitions; `coga
  block` and `coga unblock` own `blocked`; `coga launch` flips `active →
  in_progress` when it spawns the agent (and activates a draft inline first).
  Cancellation accepts every non-terminal state, requires a reason, and has no
  transition back to active.
- **Step — *where* in the workflow.** Format `N (step-name)`. Owned entirely by
  `coga bump`. A bare `coga bump` advances one step, and only while status is
  `in_progress`; a human (outside a supervised launch) can rewind with `--to`
  or `--backward` from `active`, `in_progress`, or `paused` — a rewind moves
  the step and leaves the status alone. An `active`/`paused` rewind must target
  a configured agent; human or unassigned targets require `in_progress` so the
  status-preserving move cannot strand the handoff. Rewind is an exceptional
  human debug/recovery operation: whenever guarded publication is unconfirmed,
  inspect and reconcile its retained local state before another mutating Coga
  command, branch push, or merge.

Keeping them separate is what lets you pause a task without losing its place, or
resume a blocked task at the exact step it stopped on. Tickets with no workflow
have no steps and move through statuses directly.

There's no lock file. **Status is the signal** that someone is (or isn't)
working on a task. If two people launch the same ticket, the divergence is
visible and recoverable in Git — which Coga prefers to the stale-lock, `--force`,
orphan-cleanup tax of a real mutex.

## Agents and scripts

`coga launch` decides between the two from the ticket directory alone. A
reserved `ticket.py` sibling is the ticket's deterministic half and runs as a
plain subprocess — no prompt, no agent, no TTY. Without one, launch composes a
prompt and spawns the assignee's agent CLI in a live REPL. A ticket can have
both: the script runs first and the agent continues the same step. Nothing
declares which — no mode field, no `recipe:`, no autonomy flag; the file's
presence is the whole signal, and any other attachment stays an ordinary
attachment.

Skills attached to workflow steps remain prompt contracts; workflow steps do
not become executable plugins, and Coga never imports ticket code — it
subprocesses a path. Fixed deterministic core commands stay reachable by name
through the `coga run` recipe registry, which a `ticket.py` may import from.
Recurring templates keep their deterministic half beside `ticket.md`; the
creator copies it into each period task, and a template without one launches an
agent and requires a TTY.

The two agent CLIs — **Claude Code** and **Codex** — are interchangeable.
They're configured under `[agents.*]`: committed `coga.toml` supplies shared
defaults and `coga.local.toml` overlays individual keys or adds machine-only
types. An optional `peer = "codex"` on `[agents.claude]` selects Claude's
`other-agent` reviewer; it does not select Claude as Codex's reviewer. This
global per-agent policy is intentionally the smallest third-agent escape hatch;
ticket-specific reviewer routing is deferred. No single model vendor owns your
workflow.

## Composition: how a prompt is built

`coga launch` builds one prompt, fresh, every time, by stacking layers in order:

1. Base prompt (shipped with the package).
2. Session conduct for the launch context — exactly one, so the agent reads how
   to operate before any task material.
3. This repo's context (`coga/context.md`).
4. The ticket's attached `contexts:`.
5. The ticket-level skills, then the current step's skill.
6. The ticket itself, last and contiguous within the composed prompt, in the
   order it sits on disk: the
   body's `## Description`, then its inline `## Context`, then the blackboard.

For a launch with no trailing positional arguments, that's the whole input.
When arguments are supplied, launch appends one explicit `## Launch arguments`
JSON block after the composed ticket; there is still no follow-up loading. Two
consequences worth internalizing:

- **The prompt is a pure function of the files on disk now.** Nothing is carried
  over from a previous session. That's precisely why an edit between runs takes
  effect completely and inspectably: fix the file, relaunch, done.
- **The log is deliberately never a layer.** Only the blackboard — the final
  part of the durable ticket layer — carries state forward, which is why it
  must stay small and the log can grow forever.

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
