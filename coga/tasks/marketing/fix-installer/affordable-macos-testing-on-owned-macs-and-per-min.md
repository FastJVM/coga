---
title: Affordable macOS testing on owned Macs and per-minute CI
status: active
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

Make routine macOS install testing inexpensive: use the owner's spare Apple Silicon and Intel Macs, and evaluate per-minute hosted CI for automated checks. Keep AWS EC2 Mac optional rather than the default.

Build on PR #943 (https://github.com/FastJVM/coga/pull/943) and reuse its shared install/init/validate walk. Inspect whether that PR has merged before choosing the implementation base; do not duplicate or overwrite its work.

Deliverables:
- Add a documented SSH-based path for owner-provided Macs. Use disposable macOS VMs on Apple Silicon for genuinely fresh-install tests; document the Intel compatibility path and its limits. A fresh user account does not isolate machine-wide dependencies.
- Keep destructive reset operations confined to an explicitly designated disposable test environment. Do not remove Command Line Tools from an ordinary host as an implicit setup step.
- Cover current PyPI and a wheel built from fetched main, preserving artifact/version/commit evidence, failure transcripts, and attended agent-login/first-ticket continuation.
- Compare GitHub Actions and Buildkite per-minute macOS runners with the owned-Mac path. Verify current rates, plan requirements, preinstalled software, interactive access, and ability to reproduce the missing-CLT setup experience. Recommend which checks belong in hosted CI; adding a paid service or changing the repository's no-CI posture needs an explicit owner decision.
- Document setup, reset, cleanup, and costs in the owning testing topics; keep packaged twins synchronized. Verify the driver with focused regressions and exercise an owned-Mac run when the owner supplies SSH access.

Owner decisions from 2026-10-01: two spare machines are available, one Apple Silicon and one Intel. The owner approved pursuing local Mac support, then paused implementation to discuss cost and requested this ticket. No local-Mac implementation has been made.

Cost evidence (reverify at execution): AWS Pricing API reported mac2 dedicated hosts in us-east-1 at USD 0.65/hour, with a 24-hour minimum of USD 15.60. GitHub Actions standard macOS paid usage was USD 0.062/minute (standard runners free for public repositories); Buildkite M4 Medium was USD 0.12/minute plus its required platform plan.
Sources: https://aws.amazon.com/ec2/instance-types/mac/faqs/ ; https://docs.github.com/en/billing/reference/actions-runner-pricing ; https://buildkite.com/pricing/

Outstanding AWS cleanup belongs to PR #943 and must not wait for this ticket: host h-0833c01ac15e645ac in us-east-1 was still allocated, state available with no instances, at 2026-10-01T19:29:20Z. Earliest release is 2026-10-01T23:28:57Z (4:28:57 PM Pacific). Confirm actual host release separately; stopping or terminating the instance does not stop host billing. Do not allocate more AWS resources to implement this ticket without specific spend approval.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
