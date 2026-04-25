---
name: your-namespace/your-skill
description: One sentence the agent (and the dream skill) will read to decide whether this skill applies. Be specific about when to use it.
---

# Your skill

A skill is **process knowledge** — how to do something. Write what an
agent picking this up needs to know to execute the step it's attached to.

Skills attach to **workflow steps**, not to tickets. They flow into the
prompt at launch time when the task reaches a step that references them.

## When to use this

(Optional — but useful if the description alone doesn't make it obvious.)

## How to do it

Step-by-step or just prose. Match the style of the existing skills under
`skills/` — short and direct beats long and exhaustive.

## Edge cases

(Optional — note anything subtle the agent might miss.)

## Bundled scripts

If this skill ships with scripts, list them here and explain when each is
called. The agent invokes them directly during interactive/auto sessions.
For `mode: script` tasks, `relay launch` runs the script with secrets
injected as env vars — the workflow step's `skill:` ref must point at a
skill that has a runnable script.
