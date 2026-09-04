---
slug: give-a-ticket-s-superseded-design-one-documented-h
title: Give a ticket's superseded design one documented home
status: in_progress
owner: nicktoper
human: nicktoper
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (peer-review)
---

## Description

When a ticket pivots, its `## Description` is rewritten and the abandoned direction is preserved
somewhere — but nothing documents where, so each author picks a different shape and later readers
cannot tell a live plan from a dead one. Three independent tickets in one Dream shard used three
different headings for the same thing.

Pick one convention and write it into `coga/contexts/dev/code/SKILL.md` or a new
blackboard-conventions context.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-12), classified `gap`.

Related: `v2/document-design-pivot-in-blackboard-convention` is a parked draft on the same subject —
check it for premise before starting, and fold it in or cancel it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/755
branch: docs/superseded-design-home
worktree: /home/n/Code/codex/coga-superseded-design-doc

## Plan

- Add one fixed `## Superseded designs` home to the live and packaged `dev/code` contexts.
- Keep ticket-body intent current; give each abandoned direction a dated blackboard entry naming
  its replacement and the reason for the pivot. A body note may point to the history but must not
  duplicate it.
- Cancel `v2/document-design-pivot-in-blackboard-convention` as absorbed by this ticket.
- Verify context parity, run the test suite and validation, commit, freshen against `origin/main`,
  then bump.

The alternative was a new blackboard context. It would have kept `dev/code` narrower, but no
current composition or authoring path discovers such a context; documenting the rule there alone
would leave the original gap in practice.

## Implementation

- Updated the live and packaged `dev/code` contexts with the single `## Superseded designs`
  convention and a dated entry template containing `Superseded by:` and `Reason:` lines.
- Scoped the existing “current state, not history” wording to the machine-readable `## Dev`
  fields so it no longer conflicts with retained design history.
- Kept the ticket body authoritative for current intent. It may contain a pointer to the named
  blackboard section, but not a second copy of the abandoned design.
- Canceled `v2/document-design-pivot-in-blackboard-convention` as absorbed. Its first git sync
  attempt could not resolve GitHub from the sandbox; the later PR-state sync succeeded and the
  canceled status is now present on `origin/main`.

## Verification

- `cmp` between live and packaged `dev/code`: pass.
- `git diff --check`: pass.
- `tests/test_notification_messages.py::test_recurring_create_is_silent`: passes in isolation
  after correcting its fixture to use the directory-form shape guaranteed for recurring tasks.
- `/tmp/coga-superseded-design-test-env/bin/python -m pytest`: 2,234 passed on the final base.
- `coga validate --json`: 169 tickets OK; exits 1 on unrelated existing validation debt (four
  `unsynthesized-draft-blackboard` errors plus existing warnings). No issue names these context
  changes or this ticket.

## Freshness

- Fetched and rebased cleanly onto `origin/main` at `97220cd3`, then fetched once more after the
  final test run with no new remote commits. The feature checkout is clean and two commits ahead:
  `37a53d2a` documents the convention and `4012c5e9` repairs the stale recurring-test fixture.
- Main commit `39cae10b` exposed the fixture mismatch by leasing the created recurring ticket
  before sync. The owner explicitly expanded this ticket to fix that test before opening the PR;
  production lease behavior remains unchanged and fail-loud.
