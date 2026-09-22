---
name: coga/roadmap
description: Dated sequencing and deferral guidance for Coga work; live task state owns the board, and this context only records ordering decisions.
---

# Coga roadmap

Last updated: 2026-09-22 (sequence unchanged since 2026-09-02; v2 parking
decision 2026-09-20).

This is sequencing guidance, not a cached board. Run `coga status` for the
current tasks, status, operator and step, and read ticket bodies for scope. Do
not infer present work from ticket names in an older roadmap.

## Current sequence

1. **Keep the core loop sharp.** Fix failures in create → author → launch →
   bump/mark → review before adding orchestration. Installation, package
   resources, git sync, notifications and workflow completion are part of that
   loop.
2. **Keep the explanation synchronized with code.** When a command, task
   shape or execution contract changes, update the owning context (and its
   packaged copy, if bundled) in the same PR.
3. **Treat recurring work as ordinary ticket work.** Stable `recurring/<name>`
   tasks; a template's `ticket.py` is the deterministic unattended path; Dream
   owns generic done-ticket cleanup. Operator scheduling stays outside Coga
   until a concrete scheduling design is approved.
4. **Design primitive changes before mechanical renames.** A change to a
   reserved ticket field or other shared primitive is settled in a design pass
   before contexts, stored tickets or code are renamed. Whether a particular
   rename is on the path is a question for live task state.
5. **Prefer deletion to compatibility layers**
   ([`coga/project-stage`](../project-stage/SKILL.md)).

Reliability bugs that block installation, launch, state sync or review take
precedence over new convenience surfaces. Marketing and documentation work may
proceed independently when it does not change the core task model.

## Deferred work (`coga/tasks/v2/`)

`coga/tasks/v2/` is the parking area for work not on the current execution
path; `coga status v2` is the authoritative list. Pull an item forward only
through an explicit ticket decision, then update its location/status rather
than duplicating it here.

Pulling forward starts with a premise check. A parked draft is a dated record;
its only standing re-validation is Dream's weekly premise pass, which files
findings for a human verdict. Its subject may be gone, its surfaces may no
longer resolve, its cited tickets may be retired, or something may already
have delivered it. Much of the directory predates the `relay` → `coga` rename,
which was not a find-and-replace. Read
[`coga/tasks/v2/README.md`](../../../../coga/tasks/v2/README.md) first; it holds
the premise check and the known-stale surface table. Cancelling a premise-dead
draft with a recorded reason is a normal outcome.

A bare thought — a title with nothing yet under `## Description` — is captured
only as `coga create "v2/<title>"`. Everywhere else a ticket carries its
description from creation (`coga create --description` or `coga ticket`);
`coga validate` reports live title-only tickets as `empty-description`. The
v2 README says how such a stub is read and when its describe-or-cancel verdict
is due.

### Direction change, 2026-09-20: park v2 out of reach

The owner ruled, on the canceled ticket
`interview-the-owner-on-the-17-title-only-v2-stubs` at `review-design`, that
"it's a v2 but we're far from v2 at this point": `coga/tasks/v2/` should be
parked where `coga status` does not reach, so adjudicating its title-only
stubs one by one is wasted motion (that interview would have produced 17
cancels and 0 describes). A stub that comes back is recaptured with
`coga create "v2/<title>"`.

The parking follow-up is not yet a ticket. When it is written, start its
`## Context` from what assumes the directory is live:

- `tasks.list_tasks` skips `_`-prefixed directories, so
  `git mv coga/tasks/v2 coga/tasks/_v2` would hide every draft in one commit;
- but this section, `coga/tasks/v2/README.md`, the `coga create "v2/<title>"`
  bare-capture spelling (`src/coga/create.py`, `src/coga/commands/create.py`,
  `src/coga/commands/ticket.py`, `src/coga/validate.py`), Dream's weekly premise pass, `coga/architecture`,
  `coga/codebase`, `coga/current-direction`, and `test_create`,
  `test_validate`, `test_megalaunch`, `test_ticket` all assume it is reachable;
- the open tickets
  [`adjudicate-the-eight-premise-dead-v2-drafts`](../../../../coga/tasks/adjudicate-the-eight-premise-dead-v2-drafts.md)
  and
  [`correct-the-v2-known-stale-surfaces-table-and-rout`](../../../../coga/tasks/correct-the-v2-known-stale-surfaces-table-and-rout.md)
  would need canceling or re-scoping;
- counting gotcha: `coga status v2 --all` recurses into subdirectories such as
  `cleanup-core-commands/` and excludes `README.md` indexes, so its count
  differs from `ls coga/tasks/v2/*.md`.

Until parking lands, `empty-description` warnings on title-only drafts under
`coga/tasks/v2/` are the accepted baseline (tag line
`validate-drift: empty-description`). A title-only ticket anywhere else still
needs its author's verdict.

## Sources of truth

- Live board and status: `coga status`
- Current product decisions: [`coga/current-direction`](../current-direction/SKILL.md)
- Stage posture: [`coga/project-stage`](../project-stage/SKILL.md)
- Non-negotiables: [`coga/principles`](../principles/SKILL.md)
- Exact work: the relevant ticket body and blackboard
