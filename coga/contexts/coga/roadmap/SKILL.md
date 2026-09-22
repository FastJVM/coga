---
name: coga/roadmap
description: Current sequencing guidance for Coga. Use live task state for the board; use this context only for durable ordering and deferral decisions.
---

# Coga roadmap

Last updated: 2026-09-02.

This context is sequencing guidance, not a cached board. Run `coga status` for
the current task set, status, operator, and step; read ticket bodies for scope.
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
draft is a dated record, and the only standing re-validation it gets while it
sits is Dream's weekly premise pass, which files findings for a human verdict
rather than fixing anything — so its subject may already be gone, the surfaces
it names may no longer resolve, the tickets it cites may have been retired, or
something else may already have delivered it.
Most of the directory also predates the `relay` → `coga` rename, which was not
a find-and-replace — some names carried over, some were deleted. Read
`coga/tasks/v2/README.md` before pulling anything forward; it carries the
premise check and the known-stale surface table. Cancelling a premise-dead
draft with a recorded reason is a normal outcome of that check.

A bare thought — a title with nothing yet to say under `## Description` — is
captured *only* there: `coga create "v2/<title>"`. Everywhere else a ticket
carries its description from the moment it exists (`coga create
--description`, or `coga ticket`), because a title-only ticket at the root
reads as current work in `coga status` while nobody but its author can say
what it is. `coga validate` names every live title-only ticket as
`empty-description`; `coga/tasks/v2/README.md` says how such a stub is read
and when the author's describe-or-cancel verdict is due.

**Direction change, recorded 2026-09-20.** The owner ruled — on the canceled
ticket `interview-the-owner-on-the-17-title-only-v2-stubs`, at
`review-design` — that "it's a v2 but we're far from v2 at this point":
`coga/tasks/v2/` is to be parked somewhere `coga status` does not reach, so
adjudicating its title-only stubs one by one first is wasted motion. Had the
interview's table been executed it would have been 17 cancels and 0 describes
(`pick-model-on-workflow-to-save-on-cost` included); a stub that comes back is
recaptured with `coga create "v2/<title>"`. That parking follow-up is not yet
a ticket. When it is written, start its `## Context` from this inventory of
what assumes the directory is live: `tasks.list_tasks` skips `_`-prefixed
directories, so `git mv coga/tasks/v2 coga/tasks/_v2` hides every draft in one
commit — but this section, `coga/tasks/v2/README.md`, `coga create
"v2/<title>"` as the only supported bare-capture spelling (`create.py`,
`ticket.py`, `validate.py`), Dream's weekly premise pass, `coga/architecture`,
`coga/codebase`, `coga/current-direction`, and `test_create` /
`test_validate` / `test_megalaunch` / `test_ticket` all assume it is
reachable; the open siblings `adjudicate-the-eight-premise-dead-v2-drafts`
and `correct-the-v2-known-stale-surfaces-table-and-rout` would need canceling
or re-scoping alongside. Two counting gotchas: `coga status v2 --all` reports
81 because discovery recurses into `cleanup-core-commands/` and excludes
`README.md` indexes (`src/coga/tasks.py`), while `ls coga/tasks/v2/*.md`
returns 76.

Until that parking lands, the `empty-description` warnings on `v2/` stubs are
the accepted baseline of this decision — tag line
`validate-drift: empty-description`; scope: title-only drafts under
`coga/tasks/v2/` only. A title-only ticket anywhere else still needs its
author's describe-or-cancel verdict.

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
