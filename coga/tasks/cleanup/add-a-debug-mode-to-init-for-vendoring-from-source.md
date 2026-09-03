---
slug: cleanup/add-a-debug-mode-to-init-for-vendoring-from-source
title: Add a debug mode to init for vendoring from source instead of PyPI
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

Give `coga init` an explicit debug mode that vendors the CLI from a local
source checkout instead of downloading a release from PyPI. Today the only
lever is the undocumented `COGA_REPO_URL` environment variable, so a
contributor working on an unreleased version cannot run `coga init` at all
without knowing that trick.

## Context

**The problem.** `coga init` builds a self-contained venv under
`coga/.coga/.venv` and pip-installs the *running* version into it. For a
wheel install that is `coga==<running version>` from PyPI. On an unreleased
version (this repo is `0.3.1`, PyPI serves `0.2.0`) the install fails and init
rolls back cleanly, so there is no way to init from a development checkout by
default. The audit's quickstart run had to set
`COGA_REPO_URL=/home/n/Code/coga` to get past it.

**What the owner asked for (2026-09-03).** A debug mode that makes the
build-from-source versus install-from-release distinction explicit and
documented, rather than a hidden env var contributors have to be told about.

**Design questions for the design step.** What is the surface: a flag
(`coga init --from-source [PATH]`), a documented env var, or auto-detection
when init runs from inside an editable/source install? How does the mode
appear afterwards (does `.coga/COGA_PIN` record that this repo was vendored
from source, so `coga --version` says so)? Does it interact with
`coga skill` installs, which also reach the network? Keep it small: this is
a contributor convenience, not a new packaging system.

**Related.** `docs/development.md` and `docs/releasing.md` are the docs that
should describe it. The existing `COGA_REPO_URL` handling in
`src/coga/commands/init.py` is the code path to build on.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
