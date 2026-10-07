---
title: Publish coga 1.0 as the final V1 step
status: active
owner: nicktoper
contexts:
- coga/releasing
- marketing/plan
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
agent: claude
---

## Description

Prepare and publish coga 1.0.0 to PyPI as the final V1 product-delivery step, after all remaining V1 changes and readiness checks are complete and before the public V1 launch. The 0.4.0 release published on 2026-10-02 is an interim release, not the final V1 release. Prepare a tested release candidate and release notes for owner approval, publish through the existing Trusted Publishing workflow when authorized, then verify the public package and record the release evidence.

## Context

### Ordering and scope

Owner request, 2026-10-02: this is the last V1 product-delivery ticket. Keep it
in draft until the owner confirms the remaining V1 work is complete. Follow
the release ordering in `marketing/plan`; coordinate readiness with
`marketing/build-the-launch-plan` without taking over its public launch work.

The earlier ticket `cleanup/publish-coga-1-0-to-pypi` shipped **0.4.0** despite
its historical title. The owner confirmed that release works. Its successful
install check is historical evidence, not approval to skip the final V1 gate.
Release: https://github.com/FastJVM/coga/releases/tag/v0.4.0 .

### Execution and acceptance

- Prepare the final candidate from `main` after the remaining V1 fixes land.
  Record the exact commit, readiness evidence, release notes, and proposed
  `1.0.0` version bump for the owner to review.
- Include the final README from `main` as the PyPI project description via
  `pyproject.toml` (`[project] readme = "README.md"`). Coordinate the rewrite
  with `marketing/readme-top`; keep one source rather than separate PyPI copy.
  Check the built metadata and the published PyPI description against the
  release commit's README, including Markdown rendering and documentation
  links. The 0.4.0 description was verified byte-identical to the current
  `main` README on 2026-10-02; recheck after the V1 README changes land.
- Read `coga/testing` (`docs/contexts/coga/testing/SKILL.md`) for the local
  suite and validation gate, and `coga/packaging`
  (`docs/contexts/coga/packaging/SKILL.md`) for pristine-checkout build checks.
  These are cited rather than attached. Record exact commands and results;
  do not carry forward the 0.4.0 validation exception without a new decision.
- Follow the attached release runbook. The owner approves the final candidate
  and publication; an explicitly authorized agent may assist with publishing.
  This draft does not authorize an immediate upload.
- After publishing, verify that a fresh public-index install obtains `1.0.0`,
  init and validation succeed on the documented Python floor, and the README
  first-task path works against the published artifact. Reuse the existing
  clean-install harnesses and coordinate outstanding platform and PostHog
  evidence with their owning tickets.
- Record the GitHub Release, PyPI page, workflow run, artifact hashes, and
  verification receipts. Hand the verified release links to the launch
  execution ticket before the public V1 announcement.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
