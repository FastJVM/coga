---
slug: rewrite-coga-base-prompt-and-agent-mode-block
title: Rewrite coga base prompt and agent-mode block
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/principles
- coga/codebase
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Rewrite the coga **base prompt** and the **agent-mode block** (the package
resources composed into every launch — see `compose.py` and
`src/coga/resources/`) so they read cleanly and reflect coga's current framing,
in particular the **microkernel / minimal-core** direction settled in
`decide-what-belongs-in-core-vs-skills-and-move-ski` (core holds only
command-backing and ≥2-consumer shared code; everything else is a skill recipe).

This is a prose/quality pass on the two prompts, not a behavior change to the
CLI. Goal: tighter, more legible instructions to the launched agent, aligned
with the principles and the core-vs-skills line.

## Context

- The base prompt and agent-mode block are **package resources**, not files
  under `coga/`. They live in `src/coga/resources/` and are assembled by
  `compose.py` (layers 1 in the prompt-composition order). Confirm exact paths
  before editing.
- They are composed into every launch, so length is a token cost on every
  agent run — favor tightening over adding.
- Depends conceptually on the microkernel policy landing first (that ticket
  writes the rule into `CLAUDE.md` + `coga/codebase`); this ticket makes the
  base prompt speak the same language. Fine to sequence after it.
- Out of scope: changing `compose.py` composition order or any CLI behavior;
  rewriting the `coga/` contexts (a separate concern).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
