---
title: Add an attended coga build step to the clean-install harness
status: in_progress
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
agent: claude
---

## Description

The Linux clean-install harness (`scripts/clean-install/`, contract in `coga/testing/clean-install`) stops after `coga init` and `coga validate`; its only attended continuation is `coga-clean-install ticket`. The advertised first-run command, `coga build` (alias for `launch coga-build`), is never exercised, so a release can pass the harness while onboarding is broken (see the done ticket `coga-build-fails-after-init-on-a-github-scaffolded`). The 2026-10-12 run on 0.4.0 (containers `clean-pypi-1011`, `clean-main-1011`) confirmed init leaves `coga-build` active at step 1 (gather-and-spec), but nobody launched it. Add a `coga-clean-install build [--agent NAME]` continuation to `container.sh`, mirroring `ticket`: require init-passed evidence, keep the real TTY, and record the command, exit code, and the resulting ticket status/step in evidence (not the agent conversation or login output). Update the `coga/testing/clean-install` topic and its packaged twin with the attended steps (install and log in an agent inside the container, then run it). Then run it attended on both artifacts and record whether `coga build` reaches and bumps its first step. Each failure found gets its own ticket. Also note in the topic that a retained container may be stopped (for example after a host restart) and needs `docker start` before `docker exec`. Done means the harness and docs change is merged and one attended run's evidence is in the PR.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: clean-install-build

Plan (agreed with the human): `coga-clean-install build [--agent NAME]` mirroring
`ticket` via a shared attended helper; `evidence/build.txt` records command,
coga-build `status:`/`step:` before and after (or absent), exit code, and the
scratch repo's `coga/log.md` lines for coga-build. Tests in
`tests/test_clean_install_harness.py`; topic + packaged twin updated, including
the `docker start` note. Prior 1011 containers no longer exist; the attended
run uses fresh containers.
