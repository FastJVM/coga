---
slug: install/pip-hash-requirement-breaks-editable-install
title: pip hash-checking mode breaks editable install
status: active
mode: agent
owner: zach
human: zach
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
step: 1 (implement)
---

## Description

A new user whose pip has global hash-checking mode enabled (a common managed
work-machine setting) can't run `pip install -e .` — editable installs carry no
hashes, so pip aborts. It's only workaroundable via an env var the user had to
dig to find. Make the documented install path either not depend on an editable
install for first-run, or detect the hash-checking failure and surface the exact
remediation instead of a raw pip traceback.

## Context

Reported by Greg, an external new user, on a managed work machine. The
documented quickstart leads with `pip install -e .` (CLAUDE.md "Build, Test,
and Development Commands"). This is the first domino in his install attempt — it
also caused the partial `relay init` failure tracked by
`install/init-does-not-persist-user-then-blocks-on-reinit`. Broader install
robustness is the umbrella `install/harden-packaging-and-install-before-launch`.

**Retest 2026-07-08 (fresh-container):** still broken. `PIP_REQUIRE_HASHES=1`
raw-fails both `pip install coga` ("requirements must have versions pinned")
and `pip install -e .` ("no single file to hash") with no coga-side detection
and no docs mention. Partial mitigation shipped: README now leads with
`uv tool install coga`, which ignores pip config. Remaining work: document
the uv escape hatch next to the pip instructions (README Install), and/or
detect the failure and print the remediation.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
