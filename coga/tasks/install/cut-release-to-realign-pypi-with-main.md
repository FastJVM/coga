---
slug: install/cut-release-to-realign-pypi-with-main
title: Cut release to realign PyPI with main
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
pr: https://github.com/FastJVM/coga/pull/587
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
- Resumed 2026-07-15: rebased onto current origin/main (e88729ae — only
  ticket-state commits came in), re-ran tests: 1220 passed, 1 skipped.

## Merge/publish ordering constraint — RESOLVED (2026-07-16)

The dependency PR [#579](https://github.com/FastJVM/coga/pull/579)
(`install/add-migration-errors-for-removed-config-keys`) merged on
2026-07-16, and the release branch was rebased onto a main that contains it
(`7aa23108`). Nothing blocks merging this PR and cutting the release.

## Peer review (2026-07-16)

- Native `codex review --base main` found no actionable regression in the
  one-line package metadata change.
- Rebased unconditionally onto fresh `origin/main` at `0e8dc536`; the branch
  is clean, exactly one commit ahead, and its only diff is the
  `pyproject.toml` version change. `git diff --check` passes.
- Full suite after rebase, with the packaging backend and `pip` present:
  `uv run --python 3.12 --extra test --with pip python -m pytest -q` — 1220
  passed. Source-backed smoke check reports `coga 0.3.0`.
- The first packaging-enabled run omitted `pip`, so the wheel test failed
  because its subprocess could not run `python -m pip`; the complete rerun
  above includes `pip` and passes. This was a test-environment issue, not a
  branch regression.

## Open PR (2026-07-16)

- `coga open-pr` first refused because main had moved past the peer-review
  rebase; rebased the branch onto latest `origin/main` (`433538d3`, which
  includes the #579 merge `7aa23108`), re-ran the full suite — 1270 passed —
  then re-ran `coga open-pr`, which pushed and opened
  [PR #587](https://github.com/FastJVM/coga/pull/587).
- Note: the installed `coga` at `~/.local/bin` is the stale PyPI 0.2.0 (no
  `open-pr` command — the exact skew this ticket fixes); ran the command from
  source with `uv run --python 3.12 --with-editable . coga open-pr <slug>`.

## Remaining after merge (human, per docs/releasing.md)

1. Optional TestPyPI dry run: Actions → Release → Run workflow → `testpypi`.
2. Releases → Draft a new release → tag `v0.3.0`, target `main`, publish.
3. Workflow publishes to PyPI via Trusted Publishing; verify with
   `pipx install coga && coga --version`.

## PR

### Summary

- Bump the package version from 0.2.0 to 0.3.0 so the next PyPI release
  accurately identifies the breaking behavior already on `main`.
- Keep merge and release gated on migration-errors PR #579 so existing 0.2.0
  repositories receive actionable removed-key guidance when they upgrade.

### Test plan

- `uv run --python 3.12 --extra test --with pip python -m pytest -q` — 1220 passed.
