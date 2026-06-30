---
slug: add-a-docs-oriented-review-workflow-for-docs-only
title: Add a docs-oriented review workflow for docs-only tickets
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
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
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

Found by the Dream run on 2026-06-18 (knowledge scan, gap finding G-NEW-3,
lower confidence).

Across multiple docs-only tickets (`improve-readme-and-doc`, `retire-mark-active`,
`v2/automerge-ticket`, and others), evaluators repeatedly flag that
`code/with-review`'s peer-review step (code diff review + `python -m pytest`) is
value-light for markdown/docs-only changes, yet no lighter docs-oriented review
workflow exists. The mismatch has recurred 3+ times.

This is a judgment call, hence a draft ticket rather than an auto-built
workflow: the team has tolerated the mismatch each time, so a human should
decide whether a dedicated `docs/with-review` (or similar) workflow is worth
adding, or whether the status quo is fine.

## Context

<!-- coga:blackboard -->

## Dev
branch: docs-with-review-workflow
worktree: ../coga-docs-with-review

## Decision
Human (nick) was initially unsure this should be built (ticket is a judgment
call by design). After surfacing the tradeoffs, human chose **Build
docs/with-review**.

Approach: mirror how `code/with-review` ships — identical file in both the
repo-local `coga/workflows/docs/with-review.md` and the bundled battery
`src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md`.
Reuse `code/implement` + `code/open-pr` for those steps; rewrite only the
inline **peer-review** step to be docs-oriented (review prose/accuracy/links
+ repo↔packaged sync, skip pytest unless code was actually touched). The
core complaint per the ticket is specifically the value-light code-diff +
pytest peer-review on docs-only diffs, so the change is scoped to that step.
Register the bundled path in `tests/test_packaging.py::EXPECTED_BOOTSTRAP_RESOURCES`.

Did NOT add a `docs/implement` skill — out of scope; `code/implement` is
general enough (branch/worktree/commit/bump) and the ticket's mismatch is
the peer-review step, not implement. Did NOT touch the `example/` fixture's
simplified `code/with-review` variant (fixture, not behavior).

## Implemented (step: implement)
Commit 02f25e04 on branch docs-with-review-workflow. +270 lines, 3 files:
- coga/workflows/docs/with-review.md (new, repo-local)
- src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md
  (new, bundled battery — identical to repo-local copy)
- tests/test_packaging.py (registered the bundled path in
  EXPECTED_BOOTSTRAP_RESOURCES)

Workflow shape mirrors code/with-review (implement → peer-review →
open-pr → review). Only the inline peer-review prose differs: reviews
prose/accuracy/links + repo↔packaged sync, runs pytest only if code/fixture
was actually touched. Added a "When to use this instead of code/with-review"
section and an `## implement` note clarifying the test step for docs-only work.

Verification (python3.12 / pipx coga):
- python -m pytest → 913 passed, 1 skipped
- coga validate --json → no findings reference this workflow or ticket
  (pre-existing warnings/errors on unrelated v2/* tasks only)
- both copies confirmed byte-identical

Next: peer-review (other-agent).
