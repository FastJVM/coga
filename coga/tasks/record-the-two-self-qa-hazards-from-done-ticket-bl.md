---
title: Record the two self-QA hazards from done-ticket blackboards
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: report-to-coga
    skills: []
    assignee: agent
step: 2 (human-owns-and-finishes)
---

## Description

Two self-QA hazards are recorded only in done-ticket blackboards, which Dream
deletes:

1. Stale worktree tickets — a ticket whose recorded checkout no longer exists
   or no longer matches the branch it names.
2. Simplifier coga side effects — the simplifier pass causing unintended coga
   state changes.

Give both a durable carrier, most likely a `code/self-qa` skill.

## Context

Raised by the Dream 2026-W36 knowledge scan (Phase 2, shard-01) as a `gap`.

Time pressure is real here: the source blackboards are on done tickets, and
Dream deletes an eligible done ticket in the same run that extracts from it.
Both source tickets currently carry a recorded feature checkout, so they are
retirement debt and survive until someone runs `coga retire` — but they will
not survive it. Capture the hazards before that happens.

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- branch: `self-qa-stale-ticket-and-state-side-effects`

## Agent-produces (2026-10-06)

Plan: carrier is the existing `code/self-qa` skill (no new skill). Add two
Gotchas bullets, byte-identical in `coga/skills/code/self-qa/SKILL.md` and the
packaged twin `src/coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md`.

**Draft is on the branch** (commit `a78abbb90`, pushed; no PR yet). Review with
`git diff main...self-qa-stale-ticket-and-state-side-effects`. It adds two
`## Gotchas` bullets to `code/self-qa`, plus the packaged twin.
`python -m pytest tests/test_packaging.py` passes (23). Full suite not run
because the change is skill prose only.

Sources (multiply repo, both `status: done`, both still carry `worktree:`):
- Hazard 1 — `coga/tasks/v1/clarify-production-and-probe-package-boundary.md`
  `## Self-QA (2026-08-24)`: `codex review` suggested moving the comparison
  into the architecture entrypoint "because the reviewer saw the feature
  worktree's stale pre-clarification ticket". The finding was rejected.
- Hazard 2 — `coga/tasks/v1/1-base-plugin.md` `## Self-QA`: "The simplifier's
  attempted Coga-local/log side effects were discarded". Corroborated by
  `coga/tasks/v0/7-reporting.md` `## Self-QA — 2026-09-23`: the native review
  ran Coga orientation and left unique failed-sync diagnostics in the feature
  checkout's audit log, which were preserved in a stash.

**Flag for the human — the ticket description misstates hazard 1.** It says a
"ticket whose recorded checkout no longer exists or no longer matches the
branch". The source says something different: the feature checkout's *copy of
the ticket* is stale against control, so a reviewer judges against outdated
acceptance criteria. The draft follows the source. A missing or mismatched
recorded checkout is already `dev/checkout-cleanup` territory.

Weak spots and choices to check:
- The "keep only the code edits" rule partly overlaps `## Order of operations`
  step 1 ("Commit only code on the branch") and the existing state-publication
  gotcha. It earns its place by naming the review/simplify passes as the
  source and saying to preserve, not discard, unpublished state, which matches
  `dev/checkouts` "Never discard unpublished state".
- The examples are anonymized ("one `codex review`…"), because multiply ticket
  paths would mean nothing to other repos that get the packaged skill.
- Hazard 1 arguably belongs to `dev/checkouts` as well, because peer review and
  `open-pr` also read the branch. The draft keeps it in `code/self-qa` only;
  widen it if wanted.
