---
title: Yank the PyPI 0.0.1 placeholder and document the failure
status: in_progress
owner: nicktoper
agent: claude
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
launch_generation: f1dece1b-2b78-40b5-8c42-27fa6433d123
---

## Description

On a machine whose default `python3` is 3.9 or 3.10, `pip install coga`
silently installs the 1 KB `0.0.1` placeholder: no error, no `coga` binary, no
hint about the Python version. Yank `0.0.1` on PyPI so pip reports a real
version error, and say in getting-started what the failure looks like.

## Context

**Why it survives the 1.0 release.** Publishing 1.0 does not fix this.
Every real release requires Python >= 3.11, so a 3.9 or 3.10 interpreter
resolves past them and lands on `0.0.1`, which allows Python >= 3.9.
Yanking `0.0.1` makes pip fail with "could not find a version that satisfies the requirement"
plus the Requires-Python note, which is the outcome a reader can act on.

**Two halves, two owners.**

- *Owner action on PyPI:* yank (do not delete) release `0.0.1` of the `coga`
  project. Yanking keeps the name reserved and keeps any pinned install
  working, while removing it from ordinary resolution. This is a PyPI web-UI
  action on the FastJVM account and belongs to the owner at the review step.
- *Agent action in this repo:* add a short line to
  `docs/getting-started.md` next to the "Python 3.11+" requirement saying what
  a too-old interpreter looks like, and how to check (`python3 --version`,
  or install with `uv tool install coga` which picks its own interpreter).

**Ordering.** Independent of the 1.0 release; can land before or after. The
doc line should reflect whatever Python floor
`cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` settles on.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

## Dev

branch: docs/pypi-placeholder-note
worktree: /tmp/coga-pypi-placeholder-note

## Implementation

- Commit `963f4ce6` (`Document old-Python install failures`) adds the symptoms
  and recovery beside the Python prerequisite in `docs/getting-started.md`.
  This is onboarding guidance owned by that doc.
- Kept Python 3.11+ as the floor: `pyproject.toml`'s `project.requires-python`
  remains `>=3.11`, and
  `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` chose a resource
  package marker, not a minimum-version change (currently at peer review).
- The feature checkout is separate; blackboard updates stay in the primary
  checkout. The two pre-existing modified tickets were not edited here.
- The owner must yank (not delete) PyPI `coga` 0.0.1 at the final review step.
  That external action is intentionally pending, not an implement-step blocker.

## Findings and decisions

- Live [PyPI metadata](https://pypi.org/pypi/coga/json), checked 2026-09-17:
  both 0.0.1 artifacts are unyanked and declare `Requires-Python: >=3.9`.
  The wheel is 1,049 bytes. Corrected the ticket's "no floor" claim above;
  the reported fallback on Python 3.9/3.10 is unchanged.
- The prerequisite note covers the version-error message and the old silent
  placeholder install, with `python3 --version` and Python 3.11+ as recovery.
  It does not claim the owner has already yanked the release. No runtime,
  template, context, or fixture behavior changes; no new test was added for
  this prose-only addition.
- [PyPI's yank documentation](https://docs.pypi.org/project-management/yanking/)
  confirms ordinary resolution ignores yanked releases while exact pins can
  still select them. The action belongs to the owner at review.

## Verification

- Created `/tmp/coga-pypi-placeholder-tests` with
  `python -m venv --system-site-packages /tmp/coga-pypi-placeholder-tests`, then
  installed the declared test extras from the feature checkout with
  `/tmp/coga-pypi-placeholder-tests/bin/python -m pip install --disable-pip-version-check --no-cache-dir -e '.[test]'`.
- `PYTHONPATH=/tmp/coga-pypi-placeholder-note/src /tmp/coga-pypi-placeholder-tests/bin/python -m pytest`
  — **2654 passed** on Python 3.12.12 in 183.51 seconds, including wheel
  packaging. The explicit source path ensures tests exercise this checkout.
- `git diff --check` passed. Only `docs/getting-started.md` is in the
  implementation commit; the feature checkout is clean.
- After committing, `git fetch origin main && git rebase FETCH_HEAD` succeeded
  and reported up to date with `55c072ea`. No new main commits arrived, so the
  tested source is unchanged. No push or PR during this step.
- Control-plane commands use `PYTHONPATH=/home/n/Code/codex/coga/src`:
  the global `coga` otherwise imports another checkout
  (`/home/n/Code/claude/coga`).

## Owner action at review — still pending

1. Open [the coga release management page](https://pypi.org/manage/project/coga/releases/)
   using the FastJVM owner account. For **0.0.1**, select **Options → Yank**;
   do not delete the release.
2. Suggested reason: "Placeholder release with no coga CLI. Install a current
   release using Python 3.11 or newer."
3. Confirm both 0.0.1 artifacts report `yanked: true` in the public metadata,
   then verify unpinned pip resolution for Python 3.9 and 3.10 fails with the
   Python-version explanation. Complete this action before merging the
   documentation PR or closing the review.
