---
slug: add-a-docs-oriented-review-workflow-for-docs-only
title: Add a docs-oriented review workflow for docs-only tickets
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: codex
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
step: 2 (peer-review)
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
worktree: ../coga-docs-with-review  (abs: /home/n/Code/claude/coga-docs-with-review)

## Implemented (step: implement — DONE & committed)
Commit 02f25e04. +270 lines, 3 files:
- coga/workflows/docs/with-review.md (new, repo-local)
- src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md
  (new, bundled battery — byte-identical to the repo-local copy)
- tests/test_packaging.py (registered the bundled path in
  EXPECTED_BOOTSTRAP_RESOURCES)

Decision: human (nick) was initially unsure (ticket is a judgment call), then
chose Build docs/with-review. Shape mirrors code/with-review (implement →
peer-review → open-pr → review); reuses code/implement + code/open-pr. Only the
inline peer-review prose differs: reviews prose/accuracy/links + repo↔packaged
sync, runs pytest only if code/fixture was actually touched. Added a "When to
use this instead of code/with-review" section. Did NOT add a docs/implement
skill (out of scope) or touch the example/ fixture variant.

Verification (python3.12 / pipx coga): pytest 913 passed, 1 skipped;
`coga validate --json` clean for this change (pre-existing warnings on
unrelated v2/* tasks only); both copies byte-identical; worktree clean.

## Handoff state (READ ON RELAUNCH)
Ticket is `status: active`, `step: 1 (implement)`. Implement work is already
committed (see above) — do NOT redo it.

Blocker hit this session: `coga bump` requires `in_progress` (bump.py:77), but
only `coga launch` promotes active→in_progress, and a manual session may not
self-launch (base prompt). So I activated the ticket but could not bump it.

To advance: human runs `coga launch add-a-docs-oriented-review-workflow-for-docs-only`.
The launched implement session should confirm commit 02f25e04 + this blackboard,
leave the diff as-is, and immediately `coga bump` to hand off to peer-review.
The workflow then chains normally (peer-review → open-pr → review).

## Usage

{"agent":"claude","cache_creation_input_tokens":57723,"cache_read_input_tokens":297011,"cli":"claude","input_tokens":16467,"model":"claude-opus-4-8","output_tokens":7788,"provider":"anthropic","schema":1,"session_id":"18ca7712-e5b3-4017-89cf-194c380d7817","slug":"add-a-docs-oriented-review-workflow-for-docs-only","step":"implement","title":"Add a docs-oriented review workflow for docs-only tickets","ts":"2026-06-30T21:54:14.662933Z","usage_status":"ok"}
