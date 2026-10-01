---
title: Apply three Dream W40 workflow and v2 README corrections after PR 912 lands
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

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). These stale findings target files that open PR #912 (branch `docs/v2-batch-verdicts`, "Add an Applying-a-batch-of-verdicts section to the v2 parking README") also edits, and #912 does not carry them. Apply after #912 merges or closes; keep live/packaged twins byte-identical.

1. `docs/contexts/coga/workflows/SKILL.md` "Step completion gates" (Dream shard ks-18, class stale): the `branch` gate is described as needing `branch:` **and** `worktree:` under `## Dev`, but `src/coga/step_gate.py::_has_branch_linkage` checks only a usable `branch:` (`worktree:` is recorded only for the sandbox-clone fallback). Change the bullet accordingly.
2. Same file, opening paragraph (shards ks-32, ca-03, class stale/drift): "Packaged workflows are the `code/*` loop and `docs/*`; `direct/body` ... is seeded by `coga init`." The packaged `bootstrap/workflows/` also ships `brief-for-human` and `draft-for-human`, and the init scaffold `src/coga/resources/templates/coga/workflows/` also seeds `_template`, `build/onboarding` and the recurring-job workflows. Reword (or point at the two directories instead of enumerating).
3. `coga/tasks/v2/README.md` "Title-only drafts: a capture, not a ticket" (shard ks-05, class stale): the README says the first sweep reporting a v2 stub's `empty-description` is its expiry and cites `interview-the-owner-on-the-17-title-only-v2-stubs` as batch precedent. That ticket was canceled 2026-09-20 without applying verdicts, and `coga/roadmap` "Direction change, 2026-09-20: park v2 out of reach" records v2 title-only warnings as the accepted baseline (`validate-drift: empty-description`). Scope the expiry rule to title-only tickets outside `v2/` and replace the precedent sentence.

Verification: `python -m pytest tests/test_packaging.py`.

## Context

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/934
branch: docs/w40-workflow-corrections

## Implementation plan

- PR #912 closed without merging on 2026-09-29; the dependency is cleared.
- Correct the workflow topic's branch gate and replace its incomplete workflow
  inventory with pointers to the fallback and init-seeded directories. Keep the
  canonical topic and packaged twin byte-identical.
- `src/coga/step_gate.py` `_has_branch_linkage` requires only a usable branch;
  `worktree:` is optional sandbox-clone bookkeeping.

## Already satisfied

Item 3 was superseded by merged PR #931, commit `ef0debf9d` (Park v2 as a
wish list outside discovery and Dream). `coga/tasks/v2/README.md` moved to
`coga/tasks/_v2/README.md`; its stale title-only expiry and canceled-batch
precedent are gone. The replacement explicitly says no verdict is due while
wishes are parked, and pulling one forward makes it an ordinary validated
ticket. `docs/contexts/coga/roadmap/SKILL.md`, Deferred work, records the same
2026-09-29 parking decision. Preserve this newer policy; no README edit needed.

## Implement handoff

- Commit `5b0515379` on `docs/w40-workflow-corrections` (pushed), rebased on
  `origin/main` `600bd5f73`.
- Item 1: `coga/workflows` "Step completion gates" `branch` bullet now says only
  a usable `branch:` is checked; `worktree:` is sandbox-clone bookkeeping
  (matches `step_gate._has_branch_linkage`).
- Item 2: opening paragraph no longer enumerates workflows; it points at
  `templates/coga/bootstrap/workflows/` (fallback) and
  `templates/coga/workflows/` (init-seeded, incl. `direct/body`).
- Item 3: already satisfied (see above); no README edit.
- Canonical topic and packaged bootstrap twin are byte-identical.
- Verification: `.venv/bin/python -m pytest tests/test_packaging.py` (23 passed)
  and full `.venv/bin/python -m pytest` (3135 passed). System `python` lacks
  `tomlkit`, so use the venv interpreter.

## Peer review

- `codex review --base origin/main` returned successfully with no findings.
  It confirmed the workflow paths and branch-gate description against the
  implementation; its packaging tests passed (23), as did
  `.venv/bin/python -m pytest tests/test_commands.py -k 'branch_gate' -q`
  (5 passed, 127 deselected).
- Rebased unconditionally onto fetched `origin/main` `5bdd9aaae`, without
  conflicts. Reviewed and tested commit `d03bec7ca` was pushed with
  `--force-with-lease`; no review fixes were needed.
- Post-rebase verification: `.venv/bin/python -m pytest tests/test_packaging.py`
  (23 passed); `.venv/bin/python -m pytest` (3135 passed in 205.17s).
  `git diff --check` and direct `cmp` of the canonical and packaged topics
  passed. The diff changes documentation only; no terminal or rendered
  interaction requires manual exercise.
- Independently confirmed PR #912 closed without merging and PR #931 merged
  as `ef0debf9d`; the current `_v2/README.md` and roadmap satisfy item 3.
- Returned to clean `main` at `285baf9e2` before writing this handoff.
  Main's movement since the rebase affects only another ticket and the log.

## PR

Correct the workflow topic's branch completion gate to require only a usable
`branch:`, matching the implementation, and replace the incomplete workflow
inventory with pointers to the fallback and init-seeded template directories.
Keep the canonical topic and packaged bootstrap copy byte-identical.

PR #912 is closed. The requested v2 README correction was already superseded
by merged PR #931, which parks wishes under `_v2/` with no verdict due; this
change preserves that newer policy.

Test plan: `.venv/bin/python -m pytest tests/test_packaging.py` (23 passed);
`.venv/bin/python -m pytest` (3135 passed). Codex review returned no findings.
