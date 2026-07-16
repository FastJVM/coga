---
slug: v2/minimal-ci-run-pytest-on-prs-and-tags
title: 'Minimal CI: run pytest on PRs and tags'
status: draft
owner: nicktoper
human: nicktoper
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
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

There is no CI today (`.github/workflows/` does not exist). Before tagging a
release we need a minimal GitHub Action so the release tag is trustworthy and
contributor PRs are gated.

Scope (keep it minimal):

- A workflow that runs `python -m pytest` on push to `main` and on PRs.
- Matrix on supported Python (>=3.11; at least 3.11 + one newer).
- Install the package (`pip install -e .` plus test deps) and run the suite.
- Fast and green on `main` as the acceptance bar; no flaky/networked tests in
  the required job (Slack/`gh`-dependent paths should be skipped or mocked).
- Optional follow-up (note, don't necessarily build now): a release job that
  builds the wheel / publishes to PyPI on a version tag — coordinate with
  `one-line-install`.

## Context

RC release-gate item (see `relay/roadmap`). Gives the release tag a green-checks
guarantee and protects every later Wave PR. Pairs with `one-line-install` (the
publish path) and the testing expectations in `relay/codebase`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
