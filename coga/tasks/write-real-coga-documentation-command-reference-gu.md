---
slug: write-real-coga-documentation-command-reference-gu
title: Write real coga documentation (command reference + guides)
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: docs/with-review
secrets: null
script: null
---

## Description

Stand up real Coga documentation so the README can stay minimal. The current
920-line `README.md` doubles as a full CLI manual — the companion ticket
`improve-readme` strips that down to a hook + install + key values and drops
the exhaustive command reference. This ticket is where that reference (and
proper guides) should actually live.

Scope to decide first (part of the work): **where** the docs live — a `docs/`
tree of markdown, a generated docs site, or a single `docs/reference.md`. Then
port and clean up the real content: the full `coga <command>` reference,
task/workflow lifecycle, Dream/REM, notifications, aliases, and any concepts a
new operator needs. This is a rewrite/reorganize, not a copy-paste of the old
README prose.

Done = coherent docs that a new user and a contributor can navigate, with the
README linking out to them ("Full docs →").

## Context

- **Source material:** the current `README.md` (pre-`improve-readme` rewrite)
  holds most of the raw content — the `## Commands` section (lines ~274–903),
  `## Task lifecycle`, `## External CLI Tools`, `## Layout`, notifications, and
  aliases. Pull from it, but treat it as material to reorganize, not preserve
  verbatim.
- **Canonical behavior:** `coga --help` and the `src/coga/commands/` modules
  are the source of truth for command flags/behavior — verify the reference
  against them, don't trust the old README where they disagree.
- **Voice/vision:** `docs/vision.md` and the `coga/contexts/coga/` contexts
  (principles, architecture, codebase) define the concepts and voice.
- **Sequencing:** this can proceed in parallel with or after `improve-readme`.
  Coordinate the "Full docs →" link target so the two land consistently.
- **Not yet interviewed:** this ticket was scaffolded as a follow-up during the
  `improve-readme` bootstrap. Run `coga ticket write-real-coga-documentation-command-reference-gu`
  to flesh out the docs-home decision and scope before launching.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
