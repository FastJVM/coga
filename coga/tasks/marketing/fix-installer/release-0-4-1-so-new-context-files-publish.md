---
title: Release 0.4.1 so new context files publish
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

The 2026-10-12 attended `coga build` walk on a fresh PyPI 0.4.0 install (Linux clean-install image) completed both onboarding steps, but `coga/contexts/product/vision/SKILL.md` stayed untracked. Every generated starter ticket lists `product/vision` in its `contexts:`, so a clone or a teammate gets tickets whose context file is missing. Reproduced: on 0.4.0, a sweeping command (`coga create`) commits the ticket and log but leaves the untracked context file alone; the same command on an `origin/main` wheel (da9909b2) commits it as 'Sync coga state'. Fixed on main by 4c9eff54b ('Publish every eligible file under the Coga and contexts roots', 2026-10-07), after the v0.4.0 tag (2026-10-02), and not yet released. Also, `pyproject.toml` on main still says 0.4.0, so main and the release report the same `coga --version` while behaving differently. Do: bump `version` to 0.4.1 on main; run the pre-tag gate and the TestPyPI dry run per `coga/releasing`. The human owner drafts the GitHub release (tag `v0.4.1`) and runs the PyPI publish; the agent never publishes. Afterwards, run `scripts/clean-install/run.sh pypi` against 0.4.1 and repeat the attended `coga build` walk, checking that the vision file is committed and `git status` is clean once `coga-build` is done. Done means 0.4.1 is on PyPI with that evidence recorded.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
