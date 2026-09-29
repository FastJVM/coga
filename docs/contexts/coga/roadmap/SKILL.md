---
name: coga/roadmap
description: Dated sequencing and deferral guidance for Coga work; live task state owns the board, and this context only records ordering decisions.
---

# Coga roadmap

Last updated: 2026-09-29 (sequence unchanged since 2026-09-02; v2 parking
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

## Deferred work (`coga/tasks/_v2/`)

`coga/tasks/_v2/` is a wish list, not a backlog. It is a parked directory
(defined in [`coga/tickets`](../tickets/SKILL.md)): nothing lists, launches,
validates, or scans it, so what sits there may be stale, may contradict other
wishes or `main`, and nobody reconciles it or owes a verdict on it. Capture a
wish with `coga create "_v2/<title>"`; a bare title is enough. Everywhere
else a ticket carries its description from creation (`coga create
--description` or `coga ticket`), and `coga validate` reports live
title-only tickets as `empty-description`.

Pull a wish forward only through an explicit decision: run the premise check
in [`coga/tasks/_v2/README.md`](../../../../coga/tasks/_v2/README.md), then
`git mv` it out of the parked tree (or `coga create` a fresh ticket that
cites it). Much of the directory predates the `relay` → `coga` rename, which
was not a find-and-replace; the README's known-stale surface table covers it.

The owner parked `coga/tasks/v2/` here on 2026-09-29, after ruling on
2026-09-20 ("it's a v2 but we're far from v2 at this point") that
adjudicating its drafts one by one is wasted motion.

## Sources of truth

- Live board and status: `coga status`
- Current product decisions: [`coga/current-direction`](../current-direction/SKILL.md)
- Stage posture: [`coga/project-stage`](../project-stage/SKILL.md)
- Non-negotiables: [`coga/principles`](../principles/SKILL.md)
- Exact work: the relevant ticket body and blackboard
