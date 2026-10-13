---
title: Release 0.4.1 so new context files publish
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

The 2026-10-12 attended `coga build` walk on a fresh PyPI 0.4.0 install (Linux clean-install image) completed both onboarding steps, but `coga/contexts/product/vision/SKILL.md` stayed untracked. Every generated starter ticket lists `product/vision` in its `contexts:`, so a clone or a teammate gets tickets whose context file is missing. Reproduced: on 0.4.0, a sweeping command (`coga create`) commits the ticket and log but leaves the untracked context file alone; the same command on an `origin/main` wheel (da9909b2) commits it as 'Sync coga state'. Fixed on main by 4c9eff54b ('Publish every eligible file under the Coga and contexts roots', 2026-10-07), after the v0.4.0 tag (2026-10-02), and not yet released. Also, `pyproject.toml` on main still says 0.4.0, so main and the release report the same `coga --version` while behaving differently. Do: bump `version` to 0.4.1 on main; run the pre-tag gate and the TestPyPI dry run per `coga/releasing`. The human owner drafts the GitHub release (tag `v0.4.1`) and runs the PyPI publish; the agent never publishes. Afterwards, run `scripts/clean-install/run.sh pypi` against 0.4.1 and repeat the attended `coga build` walk, checking that the vision file is committed and `git status` is clean once `coga-build` is done. Done means 0.4.1 is on PyPI with that evidence recorded.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: release-0.4.1

Plan (agreed with owner 2026-10-12): bump `pyproject.toml` version to 0.4.1
(only hard-coded `0.4.0` in the tree), run the pre-tag gate on the branch,
rerun it on the merged `main` HEAD before tagging.

## Implement handoff (2026-10-12, claude)

- Bumped `pyproject.toml` `version` 0.4.0 -> 0.4.1 (commit `6cee67362` on
  `release-0.4.1`, pushed). No other file hard-codes the version.
- Pre-tag gate ran on the branch commit (all passed): full suite, build +
  twine check, fresh py3.11 venv wheel install with `coga --version` = 0.4.1,
  `coga init --user tester` (git status clean afterwards), `coga validate --json`
  0 issues. Gotcha: the owner's shell exports bare `SLACK_WEBHOOK_URL`, which
  makes validate refuse; run it with `env -u SLACK_WEBHOOK_URL`.
- **Rerun the gate on the merged `main` HEAD before tagging** — releasing
  wants it on the exact tag commit.
- **Open: TestPyPI dry run not dispatched.** I asked the owner whether the agent should
  dispatch `gh workflow run release.yml --ref release-0.4.1 -f target=testpypi`
  (permanently uses up 0.4.1 on TestPyPI) or leave it to them after merge; no answer yet.
- Still to do after the PyPI publish (owner): `scripts/clean-install/run.sh pypi`
  against 0.4.1 plus the attended `coga build` walk, checking that the
  vision file is committed and `git status` is clean; record that evidence here.

## PR

```yaml
title: Bump version to 0.4.1
author: claude
author_evidence: Implement session ran on Claude Opus 5.5 (coga-launch 9113f2cb).
head: 6cee67362758de9cf9d98cd9418eccb74c8b3284
base: 27c20939d35bc001b9df003ab4ae6e05cd54a044
depth: skim
rationale: One-line version bump releasing the already-merged context publication fix (4c9eff54b).
implementation: Sets pyproject.toml version to 0.4.1 so main and the next release report a version distinct from 0.4.0.
deviations: TestPyPI dry run not dispatched yet; awaiting the owner's choice of who runs it.
limitations: Gate ran on the branch commit, not the eventual merge commit; rerun on main before tagging.
files:
  pyproject.toml: Bump the package version to 0.4.1.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Peer review is the next workflow step.
checks:
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q
    status: passed
    head: 6cee67362758de9cf9d98cd9418eccb74c8b3284
    base: 27c20939d35bc001b9df003ab4ae6e05cd54a044
    detail: 3600 passed in 289.21s.
  - command: uv build && uvx twine check dist/*
    status: passed
    head: 6cee67362758de9cf9d98cd9418eccb74c8b3284
    base: 27c20939d35bc001b9df003ab4ae6e05cd54a044
    detail: coga-0.4.1 wheel and sdist built; twine check PASSED for both.
  - command: fresh uv venv -p 3.11, install wheel, coga --version / coga init --user tester / coga validate --json in scratch git repo
    status: passed
    head: 6cee67362758de9cf9d98cd9418eccb74c8b3284
    base: 27c20939d35bc001b9df003ab4ae6e05cd54a044
    detail: coga 0.4.1; init ok, tree clean; validate 0 issues (with SLACK_WEBHOOK_URL unset).
```
