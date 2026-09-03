---
slug: cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f
title: Yank the PyPI 0.0.1 placeholder and document the failure
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 1 (implement)
---

## Description

On a machine whose default `python3` is 3.9 or 3.10, `pip install coga`
silently installs the 1 KB `0.0.1` placeholder: no error, no `coga` binary, no
hint about the Python version. Yank `0.0.1` on PyPI so pip reports a real
version error, and say in getting-started what the failure looks like.

## Context

**Why it survives the 1.0 release.** Publishing 1.0 does not fix this.
Every real release requires Python >= 3.11, so a 3.9 or 3.10 interpreter
resolves past them and lands on `0.0.1`, which has no floor. Yanking `0.0.1`
makes pip fail with "could not find a version that satisfies the requirement"
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
