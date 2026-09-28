---
title: Add an Applying-a-batch-of-verdicts section to the v2 parking README
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
step: 2 (peer-review)
agent: claude
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `gap` finding with no open owner. Three batch-adjudication tickets each re-derived how to apply a batch of premise verdicts under `code/with-review`. Decide whether `coga/tasks/v2/README.md` gains an "Applying a batch of verdicts" section beside "Before pulling anything forward" (note PR #845 `v2-stale-surfaces` touches that README — base on main after it lands).

**F44 — Batch-adjudication tickets re-derive the same verdict-application mechanics every time**  
(Dream 2026-W39 Phase 2, shard ks-24; class `gap`; target `coga/tasks/v2/README.md (new "Applying a batch of verdicts" section beside "Before pulling anything forward")`)

Three independent adjudication tickets each worked out, from scratch, how to actually apply a batch of premise verdicts while running under `code/with-review` (`requires: branch`, `requires: pr`): `four-parked-tickets-carry-premises-that-have-since` (done, "### Mechanics": "Verdict application is CLI state (`coga mark canceled/active/done`, `coga unblock`) on the control branch. The only PR-able work is ticket prose … `coga open-pr` treats ticket-body rewrites as publishable (`_publishable_changes`)"; and "Status is `draft`, so `coga mark done` is not allowed directly (needs `mark active` first)"), `adjudicate-parked-and-active-tickets-whose-premise` (done, "Lifecycle verdicts were applied with `coga mark` on `main` from this checkout (irreversible …); prose verdicts ride the PR", with `mark active` → `mark done` rows), and `adjudicate-the-eight-premise-dead-v2-drafts` (in_progress, "perform the sole cancellation from the control checkout before preparing cohort prose edits in the implementation checkout"). `coga/tasks/v2/README.md` owns the verdict vocabulary (cancel with reason, "already delivered by", describe-or-cancel) but says nothing about *where* each verdict is applied — lifecycle writes go to the control checkout on `main` and never ride the feature branch; only rewritten/narrowed ticket prose goes through the PR (which `open-pr` accepts as publishable); a draft that is done-by-other-means is either canceled with delivery evidence (README's current rule) or, if Retro retirement is wanted, activated first because `mark done` refuses `draft`. No context, skill, or workflow carries this (grep of `coga/contexts`, `coga/skills`, `coga/workflows` for "control checkout"/"publishable"/"mark active … mark done" in an adjudication sense returns nothing), and the open-owner grep across `coga/tasks/` for "mechanics" + "control checkout" + "adjudicat" finds only the verdict tickets themselves, none of which proposes documenting the recipe. Proposed: a short README section, and a one-line note in `coga/workflows` (the `requires:` step-gate section; `coga/internals/pr-publication` owns what `open-pr` treats as publishable) that ticket-body-only edits satisfy `requires: pr`.

## Context

<!-- coga:blackboard -->

## Dev
branch: docs/v2-batch-verdicts

## Implementation handoff

- Pushed commit `3f3c40d1a38a1ee75b410887e1fc9aa8ac702ebb` on the branch above.
  It contains `origin/main` at `909759c79`, including prerequisite PR #845
  (`cdbc0244c3ff2939a76fe3bfa42c7532aff39d44`). Returned to a clean, current
  `main` before writing this handoff. No PR opened.
- Added **Applying a batch of verdicts** beside the README's premise-check
  section: CLI lifecycle verdicts publish from `main` before prose work;
  cancellation with delivery evidence remains the default; an author opting
  for Retro activates before marking done, with activation prerequisites
  intact. Other tickets' authored bodies can be reviewed on a feature branch;
  this adjudication ticket's own state stays on `main`.
- Added the workflow PR-gate note, put the prose-only publication boundary in
  `coga/internals/pr-publication`, and clarified the matching exception in
  `dev/checkouts`. All three packaged twins match. The README links these
  owners and warns that mutating commands sweep uncommitted ticket prose
  directly to control.
- Updated the existing Dream README assertion to apply to the default premise
  verdict section, preserving the prohibition on direct draft-to-done there
  while allowing the new optional activation-then-completion recipe.
- No runtime code, frozen workflow, config, or example-fixture changes.
  The historical `src/coga/open_pr.py` `_publishable_changes` cited in the
  ticket is gone; current `open_pr` accepts committed prose subject to its
  normal checks. `src/coga/commands/mark.py` `_DONE_FROM` and
  `src/coga/mark.py` `prepare_active` substantiate the documented draft path.

## Verification

- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`:
  **3039 passed** in 187.18s. Use the checkout `.venv`; ambient `python`
  lacks declared test/runtime dependencies.
- The final rebase picked up only another ticket's lifecycle update and its
  audit line. A tree comparison confirmed every other file, including all
  implementation and test files, unchanged. Post-rebase
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q tests/test_dream_worker_templates.py tests/test_packaging.py`:
  **44 passed** in 2.55s.
- `git diff --check`: clean. All seven new relative links/anchors resolve;
  all three edited context twins are byte-identical. Remote feature ref
  matched the commit above, and `origin/main` was its ancestor at handoff.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.cli validate --task add-an-applying-a-batch-of-verdicts-section-to-the --json`:
  **1 ok, no issues**.

## Adjacent findings

- `docs/contexts/coga/workflows/SKILL.md` and its packaged twin, under
  `Step completion gates`, still say `branch` requires both `branch:` and
  `worktree:`. `src/coga/step_gate.py` `_has_branch_linkage` requires only a
  usable branch, consistent with `dev/checkouts` and `dev/dev-record`;
  `worktree:` is only for a sandbox clone. The completed
  `stop-using-worktrees` ticket records the layout change; no open follow-up
  for this stale sentence was identified. Left outside this change's scope.
- The README's pre-existing roadmap link ends in `#deferred-work`, but
  `docs/contexts/coga/roadmap/SKILL.md` names the heading
  `Deferred work (coga/tasks/v2/)`, whose generated fragment is
  `#deferred-work-cogatasksv2`. The file resolves but that old fragment does
  not; the newly added links all resolve. No follow-up identified; left
  unchanged for a focused correction.
