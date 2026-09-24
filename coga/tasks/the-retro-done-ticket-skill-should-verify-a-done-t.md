---
title: The retro done-ticket skill should verify a done ticket's claimed fix reached
  main before extracting it
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `gap` finding with no open owner. Retro (and Dream's extract path) takes a done ticket's self-reported verification at face value; two tickets show a claimed fix that never or only half reached main. Decide whether `retro/done-ticket` (packaged file is the single owner; no live twin under `coga/skills/retro/`) should require verifying the exact token/path on the control branch before treating a claim as durable knowledge, and what to record when it is not. Related extract finding F2 (`test-recurring-create-is-silent-fixture-fix-is-hal`, source done) was handed to Phase 4 Retro this run.

**F42 — A done ticket's self-reported verification is not proof its scoped change reached main**  
(Dream 2026-W39 Phase 2, shard ks-10, ks-10 (merged); class `gap`; target `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md (packaged file is the single owner; no live twin)`)

Two independent tickets record the same failure: a `status: done` ticket whose blackboard claims a fix that never (or only half) reached `main`, and every later reader — Retro, Dream, the next implementer — took the claim at face value. `coga/tasks/the-autofix-analyst-ticket-closed-without-shipping.md` (done, PR #816) documents that `fix-the-autofix-analyst` was marked done on the strength of an unrelated change (PR #724, the Claude subscription fallback) while none of the three defects its `## Description` scoped ever touched `src/coga/recurring_autofix.py`; closing it "removed the surface that would have kept the three defects visible", and the W36 backlog line that captured two of them did not drain. `coga/tasks/test-recurring-create-is-silent-fixture-fix-is-hal.md` (done) documents that `give-a-ticket-s-superseded-design-one-documented-h`'s `## Verification` claimed the fixture fix landed in `4012c5e9` when `c4482fae` carried half of it, so four later done tickets each re-recorded the failure as "pre-existing on main, worth its own ticket" and none checked the claim. The knowledge in the corpus covers only fragments: `bootstrap/dream/scan/knowledge-scan` tells the scan that a done ticket is "evidence to inspect, not an open owner" for *gap-owner* resolution, and `retro/done-ticket` says a ticket's `status: done` "says nothing about whether its adjacent bugs are fixed" and "do not ... claim one has landed" — for adjacent bugs only. Neither surface says the general rule these two tickets each had to rediscover: before Retro extracts from, deletes, or cites a done ticket as delivery evidence, compare the ticket's `## Description` acceptance scope against `main` (the named source path, test, or context) rather than against its own `## Implemented` / `## Verification` prose; a done ticket whose scoped change is absent on `main` is an unshipped ticket to report (a follow-up bug ticket, as `the-autofix-analyst-ticket-closed-without-shipping` did), not knowledge to extract or a fix to cite. No open ticket owns this (grep of `coga/tasks/` for `half-applied`, `closed without shipping`, `claimed ... landed`, `self-reported` hits only the two done tickets above). Suggested home: a short "Done is a status, not a receipt" paragraph in `retro/done-ticket`'s read-the-blackboard section, with a one-line pointer from `coga/lifecycle` (`docs/contexts/coga/lifecycle/SKILL.md`, which now owns the former `coga/contexts/coga/architecture` "Two state machines per ticket" section) (`done` is a control-plane transition and carries no proof the description shipped).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
