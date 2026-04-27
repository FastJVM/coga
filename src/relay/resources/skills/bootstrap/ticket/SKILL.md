---
name: bootstrap/ticket
description: Author a new Relay ticket. The ticket has already been scaffolded as a `draft` stub with just a title. Interview the human, scan the inventory, and fill in workflow / contexts / assignee / description. Use whenever a draft ticket is launched against this skill.
---

# Ticket

You are the authoring entry point for a new task. The human has an idea and
typed `relay create "<title>"` (or `relay launch bootstrap/ticket "<title>"`,
or invoked you inside an empty bootstrap session). A `draft` ticket has
already been scaffolded with their title — your job is to turn that stub
into a well-scoped ticket another agent (or human) can pick up cleanly.

## Step 0 — Detect your mode

Two ways you got here. Check the prompt context:

- **Factory mode (the common case).** You're inside a task directory with
  `status: draft` and a `title` set. The scaffold already happened. Skip
  Step 3. Your job is to fill in the blanks of *this* ticket.
- **Empty mode.** You're inside the `bootstrap/ticket` shim itself (no
  title, no status). The human ran `relay launch bootstrap/ticket` with no
  title. You'll need to call `relay create "<title>"` once you have enough
  to scaffold.

## Step 1 — Frame the work

Ask the human short, targeted questions. One at a time. Wait for the answer
before asking the next. Stop once you have enough to fill in the ticket —
usually two or three questions.

You're trying to surface:

- A clear, narrow title (under ~60 chars). The scaffold may have used the
  human's first phrasing — refine it if needed.
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

## Step 3 — Scaffold (empty mode only)

Skip this step in factory mode — the task is already scaffolded.

Call:

```
relay create "<title>" [--description "<one-liner>"] [--no-launch]
```

`relay create` prints the new task's slug and path. If you're already
running interactively, pass `--no-launch` so it doesn't spawn another
session on top of you. Capture the slug.

## Step 4 — Fill in the blanks

Open `relay-os/tasks/<slug>/ticket.md`. Add or refine frontmatter fields:

- `workflow:` — only if it's a real one. Setting `workflow` also implies a
  starting `step: 1 (<first-step-name>)`.
- `contexts:` — list of refs that exist on disk.
- `assignee:` — human name or agent nickname from `relay.toml`. The shim's
  default assignee is the starting point; refine if a different operator
  should own this work.
- `mode:` — `interactive`, `auto`, or `script`.
- `watchers:` — additional people who should see Slack pings.

Edit the body's `## Description` section to capture *why* and *what*. Keep
it concrete. The body is for humans; the agent reads the composed prompt at
launch.

Preserve every existing field. Use exact YAML syntax. Don't reorder for
style.

## Step 5 — Note your reasoning

Write a short paragraph to the blackboard explaining the choices you made
— which workflow you picked and why, which contexts you attached, who you
assigned. The human reads this before approving.

If you flagged a gap (no workflow fits, no context covers the domain),
write that to the blackboard too with a one-line proposal the dream skill
can act on later.

## Step 6 — Stop

Leave `status: draft`. The human flips to `active` (and runs
`relay launch <slug>`) when they're ready to start the work.

Do **not** flip the status yourself. Do **not** call `relay launch`. Do
**not** advance the step. Do **not** start doing the task itself.
Authoring is scoping; execution is a separate launch.

## What not to do

- Don't invent workflows, contexts, or skills. Reference only what exists.
- Don't bundle multiple ideas into one ticket. If the human is describing
  two unrelated things, scaffold two tasks.
- Don't write a long Description body. A few sentences with the core
  context is enough — the executor will pull more from the attached
  contexts at launch time.
- Don't fill `step` manually unless you also set `workflow`.
