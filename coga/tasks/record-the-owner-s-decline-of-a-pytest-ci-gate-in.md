---
title: Record the owner's decline of a pytest CI gate in the testing topic's CI posture
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

Filed by Dream 2026-W41, Phase 6 (knowledge scan, shard ks-17, class extract, source: canceled ticket nothing-exercises-python-3-11-the-declared-floor). Target: docs/contexts/coga/testing/SKILL.md (CI posture) and its packaged twin. Filed as a draft instead of a proposal PR because open PR #950 (https://github.com/FastJVM/coga/pull/950) edits the packaged coga/testing twin and does not carry this finding; apply after #950 lands or rebase onto it. The canceled source ticket stays on disk as evidence.

The canceled ticket records an owner decision not to act (2026-09-24): test verification is a Coga workflow property (the implement / self-qa / review steps), not a GitHub Actions gate, so PR #894 adding a Python 3.11/3.12 pytest matrix (`.github/workflows/tests.yml`) was closed unmerged; the port survives as commit 58630a20f. `docs/contexts/coga/testing/SKILL.md` "CI posture and receipts" still describes the absence of a test workflow only as a current fact and says the parked `coga/tasks/_v2/minimal-ci-run-pytest-on-prs-and-tags.md` "would change this; update this section when it lands" — it does not state that adding test CI was considered and declined, why, or that the declared 3.11 floor is therefore verified by workflow steps on a real 3.11 interpreter rather than by CI. Add one short paragraph to that section (and its packaged twin, if one exists) naming the decline, its reason, the surviving commit, and that reopening it is an owner decision (the ticket's alternative was raising `requires-python`). The 3.11 MultiplexedPath gotcha itself is already in `coga/codebase/gotchas`.

## Context

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/964
branch: docs/pytest-ci-decline

## Implementation plan

- Record the 2026-09-24 owner decline in the testing topic and its packaged
  twin, replacing the stale expectation that the parked CI proposal will land.
- Preserve workflow-owned verification and require a real Python 3.11 run
  as evidence for the declared floor; reopening CI or raising the floor
  remains an owner decision.
- Run the full suite, commit and push the documentation change, then return
  to main and hand off with one bump. No PR in this step.

## Findings

- The canceled source ticket confirms the decision and surviving commit
  `58630a20f`; Git resolves that commit to the Python 3.11/3.12 CI port.
- PR #950 is closed unmerged, with an owner rejection of its separate Codex
  review change on 2026-10-05. Its pending-edit conflict no longer applies;
  work starts from fresh main without importing the rejected change.
- This session has no `COGA_LAUNCH_RETURNS_CHECKOUT` witness; manual checkout
  start/return rules apply. Main was clean and current with origin/main.

## Implementation handoff

- Commit `0351bc601` on pushed branch `docs/pytest-ci-decline` updates
  `docs/contexts/coga/testing/SKILL.md` and its packaged bootstrap twin.
  The CI-posture paragraph records the owner decline and reason, PR #894,
  surviving commit `58630a20f`, real Python 3.11 verification, and owner
  control over reopening CI or raising `requires-python`. Removed the stale
  expectation that the parked CI proposal will land.
- No runtime, workflow, configuration, or fixture changes; no new tests
  needed for this documentation correction. No PR opened in implement.
- Verification: `PYTHONPATH="$PWD/src" .venv/bin/python -m pytest`
  (Python 3.12.12): **3274 passed in 251.25s**, then **3274 passed in
  245.63s** after rebasing onto `a1a356aa2`. Logs:
  `/tmp/coga-pytest-ci-decline.log` and
  `/tmp/coga-pytest-ci-decline-rebased.log`. These are 3.12 receipts, not
  evidence for the 3.11 floor.
- `git diff --check origin/main...HEAD` and byte comparison of both topic
  copies passed on the feature branch after the rebase.
- Pushed the branch, then returned to clean main at `99779f438`; intervening
  main changes touched only other tickets and the audit log. No unresolved
  implementation findings.

## Peer review

- `codex review --base main` returned successfully with no actionable
  findings. The initial sandbox attempt could not initialize its app-server;
  the authorized unsandboxed retry completed. Review log:
  `/tmp/coga-pytest-ci-decline-peer-review.log`.
- Checked the paragraph against the canceled source ticket and commit
  `58630a20f`. Canonical and packaged topic copies are byte-identical;
  `git diff --check origin/main...HEAD` passed. The reviewer also ran
  `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_packaging.py::test_live_and_packaged_copies_stay_identical tests/test_packaging.py::test_context_distribution_is_complete -q`:
  **2 passed in 0.47s**. This documentation-only diff has no terminal or
  rendered interactive surface to exercise.
- Unconditionally fetched origin/main and rebased onto `bf734dfe7` before
  review and testing; no conflicts or review fixes were needed. Full suite:
  `PYTHONPATH="$PWD/src" .venv/bin/python -m pytest` (Python 3.12.12):
  **3274 passed in 281.34s**. Log:
  `/tmp/coga-pytest-ci-decline-peer-pytest.log`. This is a 3.12 receipt,
  not evidence for the 3.11 floor.
- Pushed rebased commit `57c9bb417` on `docs/pytest-ci-decline` with
  `--force-with-lease`, fetched again, and returned to clean main at
  `bf734dfe7`. The feature branch remains one commit ahead. No outstanding
  findings; ready for the mechanical open-PR step.

## PR

Record the owner's 2026-09-24 decision against a pytest CI gate in the testing
topic and its packaged twin, replacing the stale expectation that the parked
CI proposal will land. Name closed PR #894 and surviving commit `58630a20f`,
explain workflow-owned verification on a real Python 3.11 interpreter, and
reserve reopening test CI or raising `requires-python` for the owner.

Test plan: `PYTHONPATH="$PWD/src" .venv/bin/python -m pytest` — 3274 passed
on Python 3.12.12; `git diff --check origin/main...HEAD` and topic byte
comparison passed. Documentation only; this run does not verify the 3.11 floor.
