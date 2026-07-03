---
slug: add-ci-to-generate-package-update-automatically-or
title: add ci to generate package update automatically (or add a recurring task)
status: active
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
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

Automate package releases so a new `coga` build becomes available without a
manual publish whenever release-worthy changes land on `main`. Two candidate
shapes — pick one during implementation and record the reasoning on the
blackboard:

- **CI**: a GitHub Actions workflow (extending the existing trusted-publishing
  `.github/workflows/release.yml`) triggered by a tag or a version bump on
  `main`, building and publishing the package.
- **Recurring task**: a `coga/recurring/` template (mode: script or agent)
  that periodically checks for unreleased changes in `src/coga/` and opens a
  release PR (version bump + changelog) for the human to merge, with CI doing
  the actual publish on merge.

Settle the trigger and versioning scheme (who bumps the version, and when)
before writing automation. Note: actual publishing to PyPI is gated on the
trusted-publisher repoint tracked in `coga-rename-follow-ups-post-repo-rename`
— if that hasn't landed, implement everything up to the publish step and call
the gate out in the PR.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
