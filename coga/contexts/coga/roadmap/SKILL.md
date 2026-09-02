---
name: coga/roadmap
description: Current sequencing guidance for Coga. Use live task state for the board; use this context only for durable ordering and deferral decisions.
---

# Coga roadmap

Last updated: 2026-09-02.

This context is sequencing guidance, not a cached board. Run `coga status` for
the current task set, status, assignee, and step; read ticket bodies for scope.
Do not infer present work from ticket names recorded in an older roadmap.

## Current sequence

1. **Keep the core loop sharp.** Fix failures in create → author → launch →
   bump/mark → review before adding new orchestration. Installation, package
   resources, git sync, notifications, and workflow completion are part of
   that loop.
2. **Keep the explanation synchronized with code.** Coga is dogfooded and
   changes quickly. When a command, task shape, or execution contract changes,
   update the matching live and packaged context/template in the same PR.
3. **Treat recurring work as ordinary ticket work.** Recurring creates stable
   `recurring/<name>` period tasks; a template's reserved `ticket.py` sibling
   is the deterministic unattended path, and Dream owns generic
   done-ticket cleanup. Operator scheduling remains outside Coga until a
   concrete scheduling design is approved.
4. **Design primitive changes before mechanical renames.** A change that
   touches a reserved ticket field, or any other shared primitive, is settled
   in a design pass before contexts, stored tickets, or code are renamed to
   match it. This is ordering guidance only: whether a particular rename is on
   the current path is a question for live task state, not for this context.
5. **Prefer deletion to compatibility layers.** Coga is pre-product. Remove
   obsolete commands, fields, and one-off process rather than preserving
   shims for historical task artifacts.

## Deferred work

The `coga/tasks/v2/` directory is the durable parking area for work not on the
current execution path. Its contents are intentionally fluid; `coga status v2`
is the authoritative list. Pull a v2 item forward only through an explicit
ticket decision, then update its location/status instead of duplicating it in
this context.

That decision starts with a premise check, not with implementation: a parked
draft is a dated record, and nothing re-validates it while it sits, so its
subject may already be gone and the surfaces it names may no longer resolve.
Most of the directory also predates the `relay` → `coga` rename, which was not
a find-and-replace — some names carried over, some were deleted. Read
`coga/tasks/v2/README.md` before pulling anything forward; it carries the
premise check and the known-stale surface table. Cancelling a premise-dead
draft with a recorded reason is a normal outcome of that check.

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
