---
slug: add-a-docs-oriented-review-workflow-for-docs-only
title: Add a docs-oriented review workflow for docs-only tickets
status: in_progress
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
step: 3 (open-pr)
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
peer-review → open-pr → review); docs-specific steps now use inline workflow
instructions so their guidance is actually composed. Peer-review prose reviews
prose/accuracy/links + repo↔packaged sync, and test guidance runs pytest only
if code/fixture was actually touched. Added a "When to use this instead of
code/with-review" section. Did NOT add a docs/implement skill (out of scope) or
touch the example/ fixture variant.

Verification (python3.12 / pipx coga): pytest 913 passed, 1 skipped;
`coga validate --json` clean for this change (pre-existing warnings on
unrelated v2/* tasks only); both copies byte-identical; worktree clean.

## Peer review (step: peer-review — DONE & committed)
Native Codex review found two real issues:
- P2: `implement` and `open-pr` had skill refs, so their inline docs-specific
  instructions would not be composed.
- P3: the architecture context list of packaged reusable workflows did not
  mention the new `docs/with-review` battery.

Commit 211a2a92 fixes both: `docs/with-review` now makes `implement` and
`open-pr` inline/self-contained steps, keeps repo and packaged workflow copies
byte-identical, and updates both live + packaged architecture contexts with
`docs/with-review`.

Verification (python3.12, `PYTHONPATH=src` where needed):
- `codex review --base main` (rerun unsandboxed after the known app-server
  read-only sandbox failure)
- workflow parser check: steps have no skill refs; inline sections are
  `implement`, `peer-review`, `open-pr`, `review`
- `python3.12 -m pytest tests/test_packaging.py -q` → 1 passed, 1 skipped
- `python3.12 -m coga.cli validate --task add-a-docs-oriented-review-workflow-for-docs-only --json` → clean
- `PYTHONPATH=src python3.12 -m pytest -p no:cacheprovider` → 913 passed, 1 skipped

## Handoff state (READ ON RELAUNCH)
Peer review is complete and committed on `docs-with-review-workflow`. Next step
is `open-pr`: use the recorded feature worktree, push branch
`docs-with-review-workflow`, open the PR, record the PR URL here, then bump to
owner review.

## Usage

{"agent":"claude","cache_creation_input_tokens":57723,"cache_read_input_tokens":297011,"cli":"claude","input_tokens":16467,"model":"claude-opus-4-8","output_tokens":7788,"provider":"anthropic","schema":1,"session_id":"18ca7712-e5b3-4017-89cf-194c380d7817","slug":"add-a-docs-oriented-review-workflow-for-docs-only","step":"implement","title":"Add a docs-oriented review workflow for docs-only tickets","ts":"2026-06-30T21:54:14.662933Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":1716736,"cli":"codex","input_tokens":109477,"model":"gpt-5.5","output_tokens":14497,"provider":"openai","schema":1,"session_id":"019f1a86-9861-71f0-bc9d-43ae6ab7bca2","slug":"add-a-docs-oriented-review-workflow-for-docs-only","step":"peer-review","title":"Add a docs-oriented review workflow for docs-only tickets","ts":"2026-06-30T22:04:50.092925Z","usage_status":"ok"}
