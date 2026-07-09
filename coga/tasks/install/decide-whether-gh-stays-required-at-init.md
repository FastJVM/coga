---
slug: install/decide-whether-gh-stays-required-at-init
title: Decide whether gh stays required at init
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

`gh` is hard-required at `coga init` (`required_at_init=True` in the
dependency manifest) even for users who never open PRs — a new install
burden Greg's original attempt didn't have. It is defensible (PR workflows
and managed skills both use it, and the check is explicit with an install
hint), but it deserves a deliberate decision: keep as-is, or demote `gh` to
point-of-need enforcement like `op` (managed skills already degrade to
warn-only when `gh skill` can't run, and `coga validate --check-github` /
launch preflight cover the PR path). Decide and either document the
rationale in the dependencies manifest or flip the flag.

## Context

Raised by the 2026-07-08 fresh-container retest (bare machine: the very
first `coga init` fails until both git and gh are installed). Touchpoint:
`src/coga/dependencies.py`; README External CLI Tools section (once it
exists — see `install/document-where-to-run-init-and-adopt-existing-repo`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
