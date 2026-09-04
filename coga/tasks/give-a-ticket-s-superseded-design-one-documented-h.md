---
slug: give-a-ticket-s-superseded-design-one-documented-h
title: Give a ticket's superseded design one documented home
status: in_progress
owner: nicktoper
human: nicktoper
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 3 (open-pr)
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

## Peer review

`codex review --base main` found two must-fix behavioral-contract mismatches:

- A draft with a conforming `## Superseded designs` archive can fail the pre-launch blackboard
  gate once the archive reaches 600 characters, because only `## Production notes` is exempt.
  The bootstrap ticket-authoring cleanup also resets a draft's blackboard wholesale, erasing the
  archive before activation. The documented home therefore needs explicit preservation in both
  contracts (or a different non-reset home).
- Prompt composition includes only top-level `## Description`, `## Context`, and the blackboard.
  The new wording says to rewrite sibling `## Acceptance Criteria`, `## Proposed Shape`, and other
  body sections, but those sections are invisible to a launched agent. Current requirements need
  to be nested under one of the two composed headings.

Owner approved the behavior fix. Commit `4e544d35` excludes only the superseded-design section
from the shared draft-synthesis check; unrelated authoring notes still fail the gate. The
ticket-authoring cleanup now preserves the archive, and live/packaged `dev/code` and architecture
contexts document preservation and placement of live requirements under composed headings.
Regression coverage checks a large archive, unrelated scratch before/after it, and actual draft
activation preserving the blackboard bytes. The existing authoring-skill assertion was updated
to require archive preservation instead of wholesale deletion.

## PR

Give abandoned ticket designs one documented home: `## Superseded designs` on the blackboard,
with dated entries recording the replacement and reason. Keep current requirements under
`## Description` or `## Context` so they appear in launch prompts.

Draft activation exempts only the archive from synthesis checks, while ticket-authoring cleanup
preserves it. Live and packaged contexts agree. Also correct the recurring-notification test
fixture to use the directory form guaranteed for recurring tasks.

Test plan: `/tmp/coga-superseded-design-test-env/bin/python -m pytest -q` — 2,236 passed;
live/packaged context parity and `git diff --check` pass. Validation reports 169 tickets OK
and the same four pre-existing draft-synthesis errors unrelated to this change.

## Peer-review handoff

- Final full suite: 2,236 passed. The first run's stale wholesale-cleanup assertion was fixed
  and the complete suite rerun successfully on the committed result.
- Both live/packaged context pairs are byte-identical; `git diff --check` passes.
- Fetched and rebased onto `origin/main` at `75e8f7c2`, then repeated fetch/rebase after the fix;
  no further remote changes. Feature checkout is clean, three commits ahead of that base:
  `a8ced8cb`, `4ea82434`, and `4e544d35`.
- Both review findings are resolved. The `## PR` section above describes the final behavior.
