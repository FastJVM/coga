---
slug: no-skill-exists-for-the-cold-evaluator-review-of-a
title: No skill exists for the cold evaluator review of a design spec
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

Several tickets carry an `## Evaluator review` section: a deliberately cold reading of a design
spec by an agent with no prior context, used to catch assumptions the author could not see. It is a
repeated, valuable ritual with no skill behind it, so each run improvises the rubric.

Write it as `coga/skills/code/review-design/SKILL.md`, or decide it belongs as a step in the
`code/design-then-implement` workflow.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-05), classified `gap`.

Note the interaction with Phase 1: `coga validate` flags `## Evaluator review` as an
`unsynthesized-draft-blackboard` authoring section on three `v2/` drafts. If this ritual becomes a
skill, the validator needs to know the section is legitimate — otherwise formalizing it makes
validate noisier, not quieter.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/752
branch: cold-design-review
worktree: /tmp/coga-cold-design-review

## Implementation plan

Add a packaged/live `code/review-design` skill and route future
`code/design-then-implement` tickets through a fresh `other-agent` evaluation
before the existing owner approval gate. Keep draft evaluator notes subject to
the current synthesis gate: the workflow review is produced only after launch,
where that validator rule does not apply.

## Implementation

- Added live and packaged `code/review-design` skills with a cold-reader rubric,
  evidence requirements, prioritized output, retry behavior, and a single bump
  into owner review.
- Added `evaluate-design` (`assignee: other-agent`) between `design` and the
  existing owner `review-design` gate in the bundled workflow.
- Updated `code/design`, `coga/current-direction`, composition coverage, and
  packaging/live-copy coverage. Existing frozen workflow snapshots intentionally
  remain unchanged.
- Kept the draft synthesis rule. A workflow evaluation is live handoff state;
  the three flagged `v2/` sections are incomplete `bootstrap/ticket` authoring
  output and remain correctly invalid before first launch.

## Verification

- `python -m pytest`: 2204 passed (isolated `/tmp` venv with `.[test]`).
- Peer review ran `codex review --base main` and found one must-fix P2 about
  live prompts misdirecting older frozen workflow snapshots.
- Applied the finding and added legacy-snapshot composition coverage; the full
  suite passed before and after the final rebase: 2205 passed.
- Rebased cleanly onto `origin/main` at `ff5d7542`. Feature commits are
  `2ec58c22` (implementation) and `8ae7f9fb` (peer-review fix).
- Focused composition and packaging tests: 8 passed.
- Post-review focused compatibility, twin-copy, and wheel checks: 4 passed.
- Targeted task validation: 1 task OK, no issues.
- `coga validate --json` in `example/coga`: 3 tasks OK, no issues.
- Full-repo validation finds only existing repository warnings and the four
  known `unsynthesized-draft-blackboard` errors; no new workflow/skill issue.
- The generic skill-creator quick validator rejects Coga's namespaced
  `code/review-design` frontmatter as non-flat; Coga's resolver, composition
  test, package build, and full suite validate the repository convention.

## Peer review

`codex review --base main` found one must-fix P2. Workflow steps are frozen,
but step skills and skill-less inline workflow prose stay live. Older
`code/design-then-implement` snapshots therefore still jump directly from
`design` to `review-design`, while the updated `code/design` skill says the
bump reaches `evaluate-design` and the updated owner prompt requires a
nonexistent `## Evaluator review`.

The proposed fix was accepted and applied. The shared `code/design` skill now
names the next frozen step rather than `evaluate-design`; the owner prompt
conditionally consumes `## Evaluator review`; and the regression composes both
steps from a pre-evaluator snapshot. The skill-creator guidance favored this
narrow, outcome-oriented correction over versioning or migrating existing
tickets.

## PR

Add a reusable cold design-review skill and route newly frozen
`code/design-then-implement` tickets through an independent `other-agent`
evaluation before owner approval. Keep draft evaluator notes under the existing
synthesis gate, preserve accurate prompts for older frozen workflow snapshots,
and cover composition plus packaged/live resource parity.

Test plan: `python -m pytest` (2205 passed), including focused composition,
live/packaged-pair, and wheel-packaging coverage.
