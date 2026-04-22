---
name: meta/create-suggest
description: Interview the human about a newly-scaffolded task, then suggest workflow + contexts + per-step skills. Writes the suggestions into the ticket frontmatter as a draft.
---

# Create-suggest

A ticket has just been scaffolded. Title and description are set. Everything
else — `workflow`, `contexts`, `step`, possibly `assignee` — is empty or
default. Your job is to fill in the blanks.

## Step 1 — Interview

You have access to a human (this is interactive mode). Ask short, targeted
questions to clarify:

- What kind of work is this? (code change, content draft, ops check,
  investigation, one-off)
- Is there an existing workflow that fits, or is this ad-hoc?
- What domain knowledge does the agent who picks this up need to have?
- Who should own this? Who should do the work?

**Ask one question at a time.** Wait for the answer. Don't batch five
questions — the human will only answer the first and ignore the rest.

Stop asking once you have enough to make concrete suggestions. Two or three
questions is usually the right number.

## Step 2 — Scan existing inventory

List the company repo's:

- Workflows: `relay-os/workflows/**/*.md`
- Contexts: `relay-os/contexts/**/SKILL.md`
- Skills: `relay-os/skills/**/SKILL.md`

Read the frontmatter `description:` of each. Match against the task.

## Step 3 — Propose

Write your suggestions into the ticket's frontmatter. Keep the existing fields
intact. Add or update:

- `workflow: <name>` — pick one that fits. If none fits, leave it blank and
  note in the blackboard that a new workflow may be needed (don't invent one
  silently).
- `contexts: [...]` — list the context refs that apply. Prefer 2–3 tight
  matches over 6 loose matches. Extra context bloats the prompt.
- `assignee:` — suggest based on who typically owns this kind of work.

Also set `step:` if you added a workflow (always `1 (<first-step-name>)`).

## Step 4 — Explain

Write a short paragraph to the blackboard's Notes section explaining *why* you
made each choice. The human reads this before confirming.

## Step 5 — Stop

Do not advance the step. Do not launch the task for real work. Set status to
`ready` (if the human approves) or leave it at `design`. The human takes it
from here.

## What not to do

- Don't invent workflows/contexts/skills. Only reference ones that exist.
- Don't fill in a long Description body — that's the human's job.
- Don't start doing the task itself. Your job is scoping, not execution.
