---
title: Preserve owner decisions not to act beyond the ticket that recorded them
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
step: 2 (peer-review)
---

## Description

Dream 2026-W35 knowledge-scan finding G2.

Owner decisions *not* to act survive only in the body of the ticket that
recorded them, and the lifecycle retires those tickets. The live example is
`decide-whether-to-keep-imported-google-agents-cli`: it was canceled without
its outcome landing in any context, so the same question is being re-raised
now (see `decide-the-fate-of-the-imported-google-agents-cli`).

A canceled ticket is not a Retro candidate -- Phase 4 only processes `done`
tickets -- so a "we looked at this and chose not to act" decision has no path
into durable knowledge at all today.

## Context

Decide where a no-action decision should land (a decision-register context,
a `## Decision` section the cancel path preserves, or a Retro rule that also
reads canceled tickets), then implement it. Relates to the existing draft
`add-decision-register-authoring-style-context`.
<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: preserve-no-action-decisions

## Plan (agreed with owner 2026-09-28)

Landing = owning topic + scan backstop. Finding: Dream's knowledge scan already
routes `extract` with `source: canceled` to a Phase 6 proposal PR, but its
qualifier excludes decisions ("abandoned design is not durable; only a gotcha,
verified behavior, measured limit"). So:
- coga/lifecycle: a no-action cancel lands the decision (what, why, revisit
  trigger) in the subject's owning topic; the ticket body is not its home.
- coga/knowledge: owner table/row for no-action decisions -> subject's topic.
- knowledge-scan + Dream Phase 6: an unlanded no-action decision on a canceled
  ticket qualifies as `source: canceled` extract.
Rejected: a separate decision-register topic (second owner, drifts);
Retro reading canceled tickets (duplicates the existing scan path).


## Implement handoff (2026-09-28)

Pushed `preserve-no-action-decisions` (one commit, rebased on origin/main):
- `coga/knowledge` (+ bootstrap twin): new paragraph naming the owning topic of
  the subject as the owner of a no-action decision (what declined, why, what
  reopens it); the ticket is never its home.
- `coga/lifecycle` (+ twin): cancellation bullet: a no-action cancel lands the
  decision in that topic before/with the cancel; reason points there; Dream
  knowledge scan is the backstop.
- `bootstrap/dream/scan/knowledge-scan/SKILL.md`: `source: canceled` qualifier
  now also admits an unlanded no-action decision. Dream Phase 6 `canceled`
  route needed no change (it already opens a proposal PR for "the durable fact").
- `tests/test_dream_worker_templates.py`: one assertion for the new qualifier.
Verification: `.venv/bin/python -m pytest` -> 3050 passed; twins byte-identical.
Not done here: the google-agents-cli decision itself lives in multiply, not this
repo; landing it is that repo's work.
