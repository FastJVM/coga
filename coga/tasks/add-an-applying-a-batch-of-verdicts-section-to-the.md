---
title: Add an Applying-a-batch-of-verdicts section to the v2 parking README
status: draft
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
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `gap` finding with no open owner. Three batch-adjudication tickets each re-derived how to apply a batch of premise verdicts under `code/with-review`. Decide whether `coga/tasks/v2/README.md` gains an "Applying a batch of verdicts" section beside "Before pulling anything forward" (note PR #845 `v2-stale-surfaces` touches that README — base on main after it lands).

**F44 — Batch-adjudication tickets re-derive the same verdict-application mechanics every time**  
(Dream 2026-W39 Phase 2, shard ks-24; class `gap`; target `coga/tasks/v2/README.md (new "Applying a batch of verdicts" section beside "Before pulling anything forward")`)

Three independent adjudication tickets each worked out, from scratch, how to actually apply a batch of premise verdicts while running under `code/with-review` (`requires: branch`, `requires: pr`): `four-parked-tickets-carry-premises-that-have-since` (done, "### Mechanics": "Verdict application is CLI state (`coga mark canceled/active/done`, `coga unblock`) on the control branch. The only PR-able work is ticket prose … `coga open-pr` treats ticket-body rewrites as publishable (`_publishable_changes`)"; and "Status is `draft`, so `coga mark done` is not allowed directly (needs `mark active` first)"), `adjudicate-parked-and-active-tickets-whose-premise` (done, "Lifecycle verdicts were applied with `coga mark` on `main` from this checkout (irreversible …); prose verdicts ride the PR", with `mark active` → `mark done` rows), and `adjudicate-the-eight-premise-dead-v2-drafts` (in_progress, "perform the sole cancellation from the control checkout before preparing cohort prose edits in the implementation checkout"). `coga/tasks/v2/README.md` owns the verdict vocabulary (cancel with reason, "already delivered by", describe-or-cancel) but says nothing about *where* each verdict is applied — lifecycle writes go to the control checkout on `main` and never ride the feature branch; only rewritten/narrowed ticket prose goes through the PR (which `open-pr` accepts as publishable); a draft that is done-by-other-means is either canceled with delivery evidence (README's current rule) or, if Retro retirement is wanted, activated first because `mark done` refuses `draft`. No context, skill, or workflow carries this (grep of `coga/contexts`, `coga/skills`, `coga/workflows` for "control checkout"/"publishable"/"mark active … mark done" in an adjudication sense returns nothing), and the open-owner grep across `coga/tasks/` for "mechanics" + "control checkout" + "adjudicat" finds only the verdict tickets themselves, none of which proposes documenting the recipe. Proposed: a short README section, and a one-line note in `coga/workflows` (the `requires:` step-gate section; `coga/internals/pr-publication` owns what `open-pr` treats as publishable) that ticket-body-only edits satisfy `requires: pr`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
