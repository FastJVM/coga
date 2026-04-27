---
name: meta/create
description: Author a new Relay task. Interview the human, scaffold the task directory by calling `relay create`, then fill in workflow, contexts, and assignee in the ticket frontmatter. Use when a human says "make a task for X" or "I want to start something new."
---

# Create

You are the authoring entry point for a new task. The human has an idea but
hasn't framed it yet. Your job is to turn that idea into a well-scoped ticket
that another agent (or human) can pick up cleanly.

`relay create` is a dumb scaffolder — it lays down a task directory with
empty frontmatter and a blank blackboard. You are the brain. You decide what
the task is, then call `relay create`, then write the rest into the ticket.

## Step 1 — Frame the work

Ask the human short, targeted questions. One at a time. Wait for the answer
before asking the next. Stop once you have enough to scaffold — usually two
or three questions.

You're trying to surface:

- A clear, narrow title (under ~60 chars).
- What kind of work this is: code change, content draft, ops check,
  investigation, one-off.
- Whether an existing workflow fits or this is ad-hoc.
- What domain knowledge the executor needs.
- Who should own it and who should do it.

Don't fish. If the human's first message is already specific, skip ahead.

## Step 2 — Scan the inventory

Before suggesting anything, read what's actually available:

- Workflows: `relay-os/workflows/**/*.md` — read each frontmatter `name` and
  `description`.
- Contexts: `relay-os/contexts/**/SKILL.md` — same.
- Skills: `relay-os/skills/**/SKILL.md` — same.

Match against the task. Prefer two or three tight matches over six loose
ones. Extra context bloats the prompt at launch.

If nothing fits, say so. Don't invent a workflow or context that doesn't
exist — flag the gap on the blackboard so the dream skill can pick it up.

## Step 3 — Scaffold

Call:

```
relay create --title "<title>" [--workflow <name>] [--context <ref>]... \
  [--owner <user>] [--assignee <nickname>] [--mode interactive|auto|script] \
  [--status design|ready]
```

Pass everything you're confident about. Leave out anything you're not — you
can edit the ticket after.

`relay create` prints the new task's `id-slug` and path. Capture both.

## Step 4 — Fill in the blanks

Open `relay-os/tasks/<id-slug>/ticket.md`. Add or refine frontmatter fields
that you couldn't pass on the CLI:

- `workflow:` — only if it's a real one. Setting `workflow` also implies a
  starting `step: 1 (<first-step-name>)`.
- `contexts:` — list of refs that exist on disk.
- `assignee:` — human name or agent nickname from `relay.toml`.
- `watchers:` — additional people who should see Slack pings.

Edit the body's `## Description` section to capture *why* and *what*. Keep
it concrete. The body is for humans; the agent reads the composed prompt at
launch.

Preserve every existing field. Use exact YAML syntax. Don't reorder for
style.

## Step 5 — Note your reasoning

Write a short paragraph to the blackboard's Notes section explaining the
choices you made — which workflow you picked and why, which contexts you
attached, who you assigned. The human reads this before approving.

If you flagged a gap (no workflow fits, no context covers the domain),
write that to Notes too with a one-line proposal the dream skill can act on
later.

## Step 6 — Stop

Set `status: ready` if the human approved during the interview. Otherwise
leave it at the default (`design`) — the human will flip it when they're
ready.

Do **not** call `relay launch`. Do **not** advance the step. Do **not**
start doing the task itself. Authoring is scoping; execution is a separate
launch.

## What not to do

- Don't invent workflows, contexts, or skills. Reference only what exists.
- Don't bundle multiple ideas into one ticket. If the human is describing
  two unrelated things, scaffold two tasks.
- Don't write a long Description body. A few sentences with the core
  context is enough — the executor will pull more from the attached
  contexts at launch time.
- Don't fill `step` manually unless you also set `workflow`.
