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

## Peer review (2026-10-13, Codex)

- Recovered the interrupted session's single unpublished audit entry with the
  normal `sync_coga_state` sweep, as explicitly authorized by the owner. The
  machine permission fix is persistent: the managed `multiply-full` profile
  now grants workspace/temp/Codex-state writes instead of root-wide writes;
  the project selects that profile. All three protected-path denials remain.
- Rebased `release-0.4.1` onto freshly fetched main, without conflicts, and
  pushed with `git push --force-with-lease origin release-0.4.1`.
  Head: `d303e5a9e1e1923c2f53c7238b6c635a50646d1e`.
  Base: `837134972e4da47f137b1feeb05b493438afdd61`.
  The complete diff remains one line in `pyproject.toml`, 0.4.0 -> 0.4.1;
  the context-publication fix `4c9eff54b` is an ancestor.
- **Required review has NOT completed.** `codex review --base main` returned
  exit 1 before starting the review: `app-server socket directory must be a
  user-owned directory with mode 0700`. An elevated retry, `--no-daemon`, and
  a fresh private TMPDIR all failed at the same startup check. These are
  returned invocation failures, not a review verdict; there are no tool
  findings to claim resolved. The attending owner was asked to run the review
  from a normal terminal, outside this session's nested sandbox. No transcript
  was present at `/tmp/coga-release-0.4.1-review.txt` when this handoff was saved.
- Current-head verification passed: full suite **3600 passed in 332.98s**
  (Python 3.12.12), build and twine checks for both distributions, and a fresh
  Python **3.11.15** wheel installation. Installed `coga --version` reports
  **0.4.1**; scratch-repo init leaves a clean tree; validation returns no issues.
  Exact commands and revisions are in `## PR` below. The first twine attempt
  could not write the default uv tools directory; the successful retry used
  temporary tool/cache directories. No UI behavior changes, so no interactive
  terminal exercise applies to this one-line diff; the installed CLI smoke ran.
- Checkout returned to clean `main` before this handoff. **No bump:** the review
  gate remains unmet. To obtain the missing review from a normal terminal,
  first `git checkout release-0.4.1`, then run
  `codex review --base main 2>&1 | tee /tmp/coga-release-0.4.1-review.txt`, wait
  for its verdict, and `git checkout main`. Record the actual reviewed head/base
  and verdict before advancing; if revisions move, refresh checks as needed.
- Release work remains: TestPyPI dry run, the pre-tag gate on the eventual
  merged/tagged main commit, owner-controlled GitHub release/PyPI publication,
  and the post-PyPI clean-install + attended build/vision-publication evidence.
  None of those publications occurred in this session.

## PR

```yaml
title: Bump version to 0.4.1
author: claude
author_evidence: Implement session ran on Claude Opus 5.5 (coga-launch 9113f2cb).
head: d303e5a9e1e1923c2f53c7238b6c635a50646d1e
base: 837134972e4da47f137b1feeb05b493438afdd61
depth: deep
rationale: One-line release version bump, but the required Codex review could not start; obtain its verdict
  before opening the PR.
implementation: Sets pyproject.toml version to 0.4.1 so the next release identifies the already-merged
  context publication fix distinctly from 0.4.0.
deviations: Required peer-review tool is blocked by nested sandbox socket-directory permissions. TestPyPI
  dry run has not been dispatched.
limitations: Successful branch checks do not replace the pre-tag gate on the eventual merged main commit.
  Owner publication and post-PyPI attended install/build verification remain outstanding.
files:
  pyproject.toml: Bump the package version from 0.4.0 to 0.4.1.
review:
  reviewer: codex
  kind: none
  status: failed
  head: d303e5a9e1e1923c2f53c7238b6c635a50646d1e
  base: 837134972e4da47f137b1feeb05b493438afdd61
  detail: 'codex review --base main returned exit 1 during startup, before reviewing the diff: app-server
    socket directory must be a user-owned directory with mode 0700. Elevated, no-daemon, and private-TMPDIR
    retries also failed. No review verdict or completed independent review.'
checks:
- command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q
  status: passed
  head: d303e5a9e1e1923c2f53c7238b6c635a50646d1e
  base: 837134972e4da47f137b1feeb05b493438afdd61
  detail: 3600 passed in 332.98s (0:05:32); Python 3.12.12.
- command: 'UV_CACHE_DIR=/tmp/coga-release-0.4.1-uv-cache uv build --out-dir /tmp/coga-release-0.4.1-peer-gate-d303e5a9/dist

    UV_TOOL_DIR=/tmp/coga-release-0.4.1-uv-tools UV_CACHE_DIR=/tmp/coga-release-0.4.1-uv-cache uvx twine
    check /tmp/coga-release-0.4.1-peer-gate-d303e5a9/dist/*'
  status: passed
  head: d303e5a9e1e1923c2f53c7238b6c635a50646d1e
  base: 837134972e4da47f137b1feeb05b493438afdd61
  detail: Built wheel and sdist; twine PASSED for both. Temporary uv tool directory resolves the default
    tools-directory write restriction.
- command: 'UV_CACHE_DIR=/tmp/coga-release-0.4.1-uv-cache uv venv --python /home/n/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11
    /tmp/coga-release-0.4.1-peer-gate-d303e5a9/venv

    UV_CACHE_DIR=/tmp/coga-release-0.4.1-uv-cache uv pip install --python /tmp/coga-release-0.4.1-peer-gate-d303e5a9/venv/bin/python
    /tmp/coga-release-0.4.1-peer-gate-d303e5a9/dist/coga-0.4.1-py3-none-any.whl

    mkdir -p /tmp/coga-release-0.4.1-peer-gate-d303e5a9/repo

    cd /tmp/coga-release-0.4.1-peer-gate-d303e5a9/repo

    git init -b main

    git config user.name tester

    git config user.email tester@example.invalid

    /tmp/coga-release-0.4.1-peer-gate-d303e5a9/venv/bin/python --version

    /tmp/coga-release-0.4.1-peer-gate-d303e5a9/venv/bin/coga --version

    env -u SLACK_WEBHOOK_URL /tmp/coga-release-0.4.1-peer-gate-d303e5a9/venv/bin/coga init --user tester

    env -u SLACK_WEBHOOK_URL /tmp/coga-release-0.4.1-peer-gate-d303e5a9/venv/bin/coga validate --json

    git status --porcelain --untracked-files=all'
  status: passed
  head: d303e5a9e1e1923c2f53c7238b6c635a50646d1e
  base: 837134972e4da47f137b1feeb05b493438afdd61
  detail: Fresh Python 3.11.15 wheel install; coga 0.4.1; init successful; validation issues=[]; Git status
    empty.
- command: git diff --check
  status: passed
  head: d303e5a9e1e1923c2f53c7238b6c635a50646d1e
  base: 837134972e4da47f137b1feeb05b493438afdd61
  detail: No whitespace errors.
```
