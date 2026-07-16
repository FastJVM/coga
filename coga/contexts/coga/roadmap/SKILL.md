---
name: coga/roadmap
description: Current sequencing guidance for Coga. Use live task state for the board; use this context only for durable ordering and deferral decisions.
---

# Coga roadmap

Last updated: 2026-07-15.

This context is sequencing guidance, not a cached board. Run `coga status` for
the current task set, status, assignee, and step; read ticket bodies for scope.
Do not infer present work from ticket names recorded in an older roadmap.

## Current sequence

1. **Keep the core loop sharp.** Fix failures in create → author → launch →
   bump/mark → review before adding new orchestration. Installation, package
   resources, git sync, notifications, and script-step completion are part of
   that loop.
2. **Keep the explanation synchronized with code.** Coga is dogfooded and
   changes quickly. When a command, task shape, or execution contract changes,
   update the matching live and packaged context/template in the same PR.
3. **Treat recurring work as ordinary ticket work.** Recurring creates stable
   `recurring/<name>` period tasks; script-backed steps are the unattended
   path, and Dream owns generic done-ticket cleanup. Operator scheduling remains
   outside Coga until a concrete scheduling design is approved.
4. **Design primitive changes before mechanical renames.** The open
   workflow-to-playbook direction changes a reserved ticket field and must be
   settled in its design ticket before contexts or stored tickets are renamed.
5. **Prefer deletion to compatibility layers.** Coga is pre-product. Remove
   obsolete commands, fields, and one-off process rather than preserving
   shims for historical task artifacts.

## Deferred work

The `coga/tasks/v2/` directory is the durable parking area for work not on the
current execution path. Its contents are intentionally fluid; `coga status v2`
is the authoritative list. Pull a v2 item forward only through an explicit
ticket decision, then update its location/status instead of duplicating it in
this context.

Marketing and documentation work may proceed independently when it does not
change the core task model. Reliability bugs that block installation, launch,
state sync, or review take precedence over new convenience surfaces.

## Sources of truth

- Live board and status: `coga status`
- Current product decisions: `coga/current-direction`
- Stage posture: `coga/project-stage`
- Non-negotiables: `coga/principles`
- Exact work: the relevant ticket body and blackboard

## What this context does NOT cover

- A frozen ticket census or release checklist.
- The reasoning behind product decisions; see `coga/current-direction`.
- The complete backlog; use `coga status` and the task tree.
