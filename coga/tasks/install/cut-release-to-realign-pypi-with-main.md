---
slug: install/cut-release-to-realign-pypi-with-main
title: Cut release to realign PyPI with main
status: active
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
