---
title: Linux clean-install harness
status: draft
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
step: 1 (implement)
---

## Description

Build and commit a reusable Linux clean-install harness, so installer issues
can be reproduced from nothing and each fix can later be proven with the same
run. The harness has three parts:

- a Docker image based on Python 3.11 (the declared floor) with a fresh
  non-root user and nothing preinstalled beyond the prerequisites that
  `coga/install` lists;
- a script that installs Coga into it from either **the current PyPI
  release** or **a wheel built from `main`** with `uv build` (chosen by an
  argument), then walks the documented path: `uv tool install coga`,
  `coga --version`, `git init` of a scratch repo, `coga init --user <name>`,
  and `coga ticket "<first task>"`;
- a short runbook covering how to build, run, and drop into the container
  interactively for the attended agent-login and first-task steps.

Done means the harness and runbook are merged via PR, and one run per
artifact reaches `coga init` (or records exactly where it failed) in the PR
description. This ticket does not file or fix installer issues; that is
`marketing/fix-installer/run-clean-installs-and-file-issues`.

## Context

Part of the `marketing/fix-installer/` set, which replaced the single
`marketing/fix-installer` ticket (V1 prerequisite for
`marketing/build-the-launch-plan`). Sibling tickets: `macos-clean-install-harness-on-aws`
and `run-clean-installs-and-file-issues`. The Windows (`v2/windows-native-clean-install`)
and CI matrix (`v2/install-smoke-ci-matrix`) work is deferred to V2.

The expected behavior is the documented path. It is cited, not attached, in
`README.md` and in the `coga/install`, `coga/init` and `coga/first-task`
topics (`docs/contexts/coga/<ref>/SKILL.md`). `coga/install` prerequisites:
Python 3.11+ (`tomllib`), git (the only tool `coga init` enforces), an
authenticated agent CLI for `launch`/`ticket`/`build`, `gh` recommended, and
`op` only for `op://` secrets. Note that `README.md` currently has two
"Getting Started" blocks that disagree (one still says `coga build`); follow
the topics and leave the README to `marketing/readme-top`.

The harness is repo dev tooling, not package code. It stays out of
`src/coga/` (`coga/extension-model` microkernel rule); place it per
`coga/codebase` and `coga/testing` (both cited). Keep it minimal: no new
installer tier or onboarding framework. Test the installed artifact, not an
editable tree.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
