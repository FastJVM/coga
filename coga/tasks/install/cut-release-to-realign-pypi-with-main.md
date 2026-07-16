---
slug: install/cut-release-to-realign-pypi-with-main
title: Cut release to realign PyPI with main
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- dev/code
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
script: null
step: 2 (peer-review)
---

## Description

Main has drifted from the published 0.2.0 wheel with breaking changes and no
version bump — `pyproject.toml` still says 0.2.0 while HEAD removed the
`[agents.*] auto` config key, hard-requires `coga init --user`, requires
`user` at config load for every command, dropped the `autonomy` field/column,
and renamed "panic" → "block" in notification text. Because `coga init`
vendors main HEAD (see the vendor-cli sibling ticket), this skew ships to
every fresh init today. Bump the version (0.3.0), cut the release per
`docs/releasing.md`, and publish — after the migration-error ticket lands so
upgraders get actionable errors instead of generic unknown-key failures.

## Context

Found in the 2026-07-08 fresh-container retest: PyPI 0.2.0 and `pip install
/src` both report `coga 0.2.0` yet behave differently on init/--help/config.
Depends on: `install/add-migration-errors-for-removed-config-keys` (land
first), ideally `install/vendor-cli-from-installed-package-not-git-clone`.
Touchpoints: `pyproject.toml` version, `docs/releasing.md` process.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: release-0.3.0
worktree: /home/n/Code/claude/coga-release-0.3.0

## Implement (2026-07-15)

- Code change is a one-liner: `pyproject.toml` version `0.2.0` → `0.3.0`.
  Verified the version is not hardcoded anywhere else — `cli.py` reads it via
  `importlib.metadata.version("coga")`, so no other file needs touching.
- Tests: `uv run --python 3.12 --with pytest python -m pytest -q` in the
  worktree — 1207 passed, 1 skipped. (System default python is 3.9; repo needs
  3.11+, so use uv or /usr/bin/python3.12.) Smoke check: `coga --version` from
  the worktree reports `coga 0.3.0`.
- Branch is based on origin/main HEAD (a180b4aa) as of this session.

## ⚠ Merge/publish ordering constraint

The dependency ticket `install/add-migration-errors-for-removed-config-keys`
has NOT landed yet (still at step 1, implement; `src/coga/config.py` on main
has no migration carve-out for the removed `[agents.*] auto` key). Per this
ticket's description, 0.3.0 must be **published after** that ticket lands so
upgraders get actionable errors. The version bump itself is safe to review
now, but **do not merge this PR / cut the GitHub release until the
migration-errors PR is on main.**

## Remaining after merge (human, per docs/releasing.md)

1. Optional TestPyPI dry run: Actions → Release → Run workflow → `testpypi`.
2. Releases → Draft a new release → tag `v0.3.0`, target `main`, publish.
3. Workflow publishes to PyPI via Trusted Publishing; verify with
   `pipx install coga && coga --version`.

## Usage

{"agent":"claude","cache_creation_input_tokens":117699,"cache_read_input_tokens":1721738,"cli":"claude","input_tokens":76,"model":"claude-fable-5","output_tokens":23284,"provider":"anthropic","schema":1,"session_id":"52115c07-7d44-4bf0-b3fe-cb97b1c67a16","slug":"install/cut-release-to-realign-pypi-with-main","step":"implement","title":"Cut release to realign PyPI with main","ts":"2026-07-16T00:00:04.545170Z","usage_status":"ok"}
