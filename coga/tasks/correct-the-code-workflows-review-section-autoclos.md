---
title: 'Correct the code workflows'' review section: autoclose now disposes of checkouts'
status: done
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
agent: claude
---

## Description

Filed by Dream 2026-W41, Phase 6 (contract audit, shard ca-05, class drift). Target: src/coga/resources/templates/coga/bootstrap/workflows/code/{design-then-implement,with-review,with-self-review}.md, the `## review` section. Filed as a draft instead of a proposal PR because open PR #950 (https://github.com/FastJVM/coga/pull/950, Codex peer review) edits with-review.md and does not carry this finding; apply after #950 lands or rebase onto it.

`design-then-implement.md` line 78, `with-review.md` line 151, and `with-self-review.md` line 76 (all under `src/coga/resources/templates/coga/bootstrap/workflows/code/`, the `## review` section) state that a done ticket's feature branch and recorded worktree "outlive the close: neither the sweep nor `coga bump` disposes of them, because destructive behavior is never implicit", leaving disposal solely to `coga retire <slug>`. Code reality contradicts this: `coga.autoclose.run_autoclose_recipe` calls `_dispose_checkouts`, which disposes of each closed ticket's recorded `branch:`/`worktree:` (and every open `retires.md` worklist entry) under the shared `coga.checkout_disposal` proofs, and `coga/skills/coga/autoclose/sweep/SKILL.md` ("The retire follow-up", lines 37-45) documents that the sweep "now runs the deterministic, narrow, named rule itself" because the named-only design built an unworked backlog. Source of truth: `src/coga/autoclose.py` (`_dispose_checkouts`, `run_autoclose_recipe`). The three workflow `## review` sections should say the autoclose sweep disposes of provably-safe checkouts on close and that `coga retire` remains the path for the retro and for checkouts a proof preserved.

Done when the three shipped workflow review sections say the autoclose sweep disposes of provably-safe checkouts on close (src/coga/autoclose.py _dispose_checkouts) and that `coga retire` remains the path for the retro and for checkouts a proof preserved; tests/test_packaging.py passes.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/965
branch: fix-code-workflow-review-autoclose-disposal

Plan: rewrite the `done is not the end` paragraph in the three packaged code
workflows (no live twin under `coga/workflows/code/`). Key nuance from
`autoclose._dispose_checkouts`: only tickets *the sweep* closes (plus open
`retires.md` entries) get disposal; a `coga bump` close does not dispose.
PR #950 is CLOSED unmerged, so no rebase dependency.

## Implement handoff

- Commit on `fix-code-workflow-review-autoclose-disposal` (pushed) rewrites the
  `done is not the end` paragraph of the `## review` section in
  `bootstrap/workflows/code/{design-then-implement,with-review,with-self-review}.md`
  identically: the sweep disposes of provably-safe checkouts of tickets it
  closes (`coga.autoclose._dispose_checkouts`, shared `coga.checkout_disposal`
  proofs), preserved ones land on `retires.md`; a `coga bump` close disposes of
  nothing; `coga retire` stays the path for the retro and leftover checkouts.
- No live twin exists (`coga/workflows/code/` absent); packaging test passes.
- Tests: `python -m pytest` → 3273 passed, 1 failed:
  `tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`
  — fails identically on clean `main` (recurring ticket.py ordering:
  `autoclose-merged` vs `_custom-phone-home`); unrelated, not fixed here.
- Adjacent (not fixed, out of ticket scope):
  `bootstrap/workflows/docs/with-review.md` carries the same stale
  "outlive the close" paragraph; needs the same correction in a follow-up.

## Peer review

- `codex review --base main` returned successfully with no must-fix findings.
  It confirmed the disposal/retry behavior and the distinction from manual
  bump and retire; its targeted packaging checks passed (3 passed).
- Independently checked the three identical replacement paragraphs against
  `autoclose._dispose_checkouts`, `run_autoclose_recipe`, and
  `dev/checkout-cleanup`. This is prose-only; no terminal or rendered
  interaction changed. No review fixes were needed.
- Ran `git fetch origin main && git rebase FETCH_HEAD` successfully onto
  `bf734dfe7`; pushed commit `f07fe6fb9` with `--force-with-lease`.
  Returned to clean, current `main`, with one feature commit ahead.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest`:
  **3274 passed**, including all 23 tests in `tests/test_packaging.py`.
  The implementation-stage legacy-adoption failure did not reproduce.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task correct-the-code-workflows-review-section-autoclos --json`:
  1 valid task, no issues. `git diff --check` passed.

## PR

Correct the review sections in the three shipped code workflows to describe
autoclose's existing cleanup: the sweep disposes of provably-safe recorded
checkouts and retries preserved ones through `retires.md`. Clarify that a
manual `coga bump` close does not dispose of checkouts, and `coga retire`
remains the path for the retro and any checkout the sweep preserved or never
saw. No runtime behavior changes; these workflows have no live twins.

Test plan: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` — 3274 passed (including all 23 packaging tests); `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task correct-the-code-workflows-review-section-autoclos --json` — no issues; `git diff --check` passed.
