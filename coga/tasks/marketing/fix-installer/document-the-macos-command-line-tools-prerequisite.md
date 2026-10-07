---
title: Document the macOS Command Line Tools prerequisite
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
launch_generation: pending:78ff9271-79de-4442-b880-fac5f3d20fc5
---

## Description

Reproduced 2026-10-01 on fresh macOS 27.0 (26A428), arm64 EC2 mac2.metal, AMI ami-0531fecfb292182a3. Exact harness command: AWS_PROFILE=multiply-telemetry ./scripts/clean-install/aws-mac.sh walk installer-mac-20261001 pypi cltprobe nicktoper. First failing command: git --version (exit 1), output: xcode-select: error: No developer tools were found and no install could be requested (possibly because there is no active GUI session). Python and Coga artifact resolution were not reached; intended matrix is Python 3.11 with current PyPI release and main wheel. This machine prerequisite affects both artifact paths before installation; neither artifact was installed in this probe. The harness deliberately removes the AMI CLT to reproduce a fresh Mac. Expected: the documented prerequisites explain the first Git invocation, graphical CLT install prompt, and an actionable SSH/headless path before telling users to git init or coga init. Suggested fix owner: docs/contexts/coga/install/SKILL.md and its packaged twin, linking the existing coga/testing/clean-install/macos-aws runbook as appropriate. Coordinate README wording with marketing/readme-top; do not duplicate that ticket or add an automatic Coga installer. Evidence: .coga/clean-install/installer-mac-20261001/walks/cltprobe/mac/evidence/steps.txt and transcript.txt. The SSH error is observed; the GUI dialog was not exercised. A headless softwareupdate CLT install is the test-machine workaround. Prior independent reproduction is recorded in marketing/fix-installer/macos-clean-install-harness-on-aws. Parent findings: marketing/fix-installer/run-clean-installs-and-file-issues.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
