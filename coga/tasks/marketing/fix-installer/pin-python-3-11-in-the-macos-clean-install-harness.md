---
title: Pin Python 3.11 in the macOS clean-install harness
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
launch_generation: pending:009a4925-56da-4370-8fd9-a207ef679970
---

## Description

The macOS harness does not enforce the required Python 3.11 matrix, unlike Linux. Repro OS: macOS 27.0 (26A428), arm64 EC2 mac2.metal AMI ami-0531fecfb292182a3. After CLT installation, /usr/bin/python3 --version prints Python 3.9.6. scripts/clean-install/macos-walk.sh walk installs uv then invokes container.sh without UV_PYTHON or a Python provision/check. Prior unmodified macOS PyPI walk resolved coga 0.0.1 with no executable (2026-09-30, recorded in macos-clean-install-harness-on-aws). Current 2026-10-01 test-only workaround adds uv python install 3.11, UV_PYTHON=3.11, UV_PYTHON_DOWNLOADS=never and the managed interpreter bin directory to PATH: AWS_PROFILE=multiply-telemetry ./scripts/clean-install/aws-mac.sh walk installer-mac-20261001 pypi pypi311 nicktoper then reports Python 3.11.16, uv 0.12.21, Coga 0.2.0 and reaches init. Expected: the shared Linux/macOS matrix explicitly selects and records Python 3.11, refusing or provisioning the prerequisite rather than silently testing another interpreter. Applies to both main and PyPI artifact selection; this is a current harness gap, not a Coga 0.0.1 release regression. Suggested fix: scripts/clean-install/macos-walk.sh, macOS runbook docs/contexts/coga/testing/clean-install/macos-aws/SKILL.md and packaged twin, with appropriate harness tests. Existing macos-clean-install-harness-on-aws owns the merged original harness; this draft isolates the newly confirmed interpreter-contract gap. Evidence: .coga/clean-install/installer-mac-20261001/walks/pypi311/, and parent marketing/fix-installer/run-clean-installs-and-file-issues. Do not change package Python floor or publish a release.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
