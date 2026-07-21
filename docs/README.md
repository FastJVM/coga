# Coga documentation

Coga is a small CLI and a markdown operating system for teams that run work with
coding agents. Tickets, context, workflows, skills, blackboards, and corrections
all live as plain files in your repo, versioned by Git and read by the same
humans and agents that do the work.

If you're new, read these in order:

1. **[Getting started](getting-started.md)** — install Coga, adopt it into a
   repo, and take a first task from draft to a merged PR. Start here.
2. **[Concepts](concepts.md)** — the mental model: tickets, the blackboard,
   contexts vs. skills, workflows and steps, the two state machines, agents vs.
   scripts. Read this once and the rest of the system stops surprising you.
3. **[Command reference](reference.md)** — every public `coga` command, its
   arguments and flags, generated from the CLI's own help.

Then, as you need them:

- **[Operations](operations.md)** — running Coga day to day: notifications,
  aliases, recurring maintenance (Dream and REM), the digest, and secrets.
- **[Development](development.md)** — working on Coga itself: source layout,
  running from a checkout, tests, and the repo↔package sync rule.

## The wider picture

- **[Vision](vision.md)** — the essay: why Coga exists, the classical-vs-romantic
  framing, and the thesis behind a two-person team running like ten. This is the
  "why"; the docs above are the "how."
- **[Migrating to Coga](migrating-to-coga.md)** — moving an existing operation
  onto the substrate.
- **[Releasing](releasing.md)** — cutting a Coga release (contributor-facing).

## The shortest possible summary

You adopt Coga into a Git repo with `coga init`. Work becomes **tickets** —
markdown files under `coga/tasks/`. A ticket carries a **workflow** (its ordered
steps) and a **blackboard** (its shared scratch memory). `coga launch` composes
a ticket's context into a prompt and hands it to an agent CLI (Claude Code or
Codex); the agent does the step's work, writes what it learned to the
blackboard, and runs `coga bump` to advance. When the agent gets something
wrong, you fix the context or workflow it used and commit the diff — the next
run starts from the corrected version. Nothing is hidden: every rule the agent
follows is a file you can open and edit.
