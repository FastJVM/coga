---
title: macOS clean-install harness on AWS
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
secrets:
  - AWS_PROFILE: env:AWS_PROFILE
---

## Description

Build and commit scripts that provision a clean macOS machine on AWS EC2 Mac
(a `mac2` dedicated host), install Coga there from **the current PyPI
release** or **a wheel built from `main`**, walk the same documented path as
the Linux harness, and tear everything down. Include a short runbook: region
choice, how the owner logs in (SSH, or VNC for GUI flows) for the agent login
and first-task steps, and the teardown and host-release procedure.

Done means the scripts and runbook are merged via PR, and one provision →
install → `coga init` → teardown cycle has been exercised, with the resource
IDs and outcome in the PR description. This ticket does not file or fix
installer issues; that is `marketing/fix-installer/run-clean-installs-and-file-issues`.

## Context

Part of the `marketing/fix-installer/` set (V1). Siblings:
`linux-clean-install-harness` (reuse its install/walk script so both OSes run
the same steps) and `run-clean-installs-and-file-issues`.

**AWS.** Credentials come from an SSO profile named by `AWS_PROFILE`
(declared in `secrets:`); the owner runs `aws sso login --profile <p>` before
launch. Ask the owner before creating any instance or dedicated host, because
it costs money: a `mac2.metal` host has a 24-hour minimum allocation (roughly
$25–30) and can only be released after 24 hours. Check the dedicated-host
quota and pick the region with the owner, since `mac2` capacity varies by
region. Record every resource ID on the blackboard, and release or terminate
everything so nothing is orphaned. Never use the AWS root credentials in
1Password.

**Fresh macOS.** The first `git` call triggers the Xcode Command Line Tools
install prompt. The harness should reproduce that as a new user would see it,
not preinstall CLT silently. The owner has decided it counts as a finding
(filed by the run ticket).

The expected path is cited, not attached: `coga/install`, `coga/init` and
`coga/first-task` (`docs/contexts/coga/<ref>/SKILL.md`). The harness is dev
tooling outside `src/coga/` (`coga/extension-model`). No new installer tier.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
