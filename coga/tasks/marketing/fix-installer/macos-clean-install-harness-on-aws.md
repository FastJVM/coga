---
title: macOS clean-install harness on AWS
status: blocked
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

**AWS.** Credentials come from the owner's AWS SSO profile (currently
`multiply-telemetry`); the owner runs `aws sso login --profile <profile>`
before launch. The profile name is not a secret, so the ticket declares no
`secrets:`; pass `--profile` (or export `AWS_PROFILE`) in every `aws` call. Ask the owner before creating any instance or dedicated host, because
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

## Dev

branch: macos-clean-install-harness

## Plan — 2026-09-30 (claude, megalaunch)

- Host driver `scripts/clean-install/aws-mac.sh` (preflight / provision /
  walk / vnc / teardown / release), Mac-side `scripts/clean-install/macos-walk.sh`
  that resets CLT, creates a fresh macOS user, installs uv with its official
  installer, then runs the shared walk script `container.sh` unchanged in steps.
- Runbook as child topic `coga/testing/clean-install/macos-aws` (+ packaged twin).
- Spending AWS money needs owner approval (region + host allocation); the AWS
  SSO token for `multiply-telemetry` was expired at session start.

## Implementation handoff — 2026-09-30 (claude, megalaunch)

Pushed `macos-clean-install-harness` (one commit on top of `origin/main`
`86ccdc662`). No AWS resources have been created. **The provision cycle has
not been exercised yet**: it needs an owner-approved spend and a live SSO
token (the `multiply-telemetry` token had expired this session). Blocked on that.

What changed:
- `scripts/clean-install/aws-mac.sh` (host driver): `preflight REGION`
  (read-only: quota, mac2 AZs, existing hosts, newest AMI), `provision NAME
  REGION AZ` (gated by `COGA_CLEAN_INSTALL_ALLOCATE=yes`; key pair, SG with SSH
  from caller /32 only, host, instance, and each ID appended to
  `.coga/clean-install/NAME/resources.env` as it is created), `walk NAME
  pypi|main MAC_USER [OPERATOR]`, `ssh`, `vnc` (Screen Sharing via SSH
  tunnel, 5900 never opened), `status`, `teardown` (terminate → SG → key →
  release; idempotent), `release` (retry after 24h).
- `scripts/clean-install/macos-walk.sh` (Mac side, Bash 3.2): `baseline`,
  `reset` (removes AMI's CLT + receipts; asserts fresh login shell's git is
  the `/usr/bin` shim, so the first git call prompts as for a new user),
  `walk` (new macOS user, uv official installer, then shared `container.sh`),
  `ticket`, `vnc`.
- `container.sh`: `git --version` now runs before `python3 --version` (macOS
  has no `python`; git is where CLT prompt should surface), and a
  `shasum -a 256` fallback. Linux steps otherwise unchanged.
- Runbook topic `coga/testing/clean-install/macos-aws` + packaged twin,
  registered in `REQUIRED_BOOTSTRAP_CONTEXT_REFS`; linked from
  `coga/testing` and `coga/testing/clean-install`.
- Tests: `test_aws_mac_*` in `tests/test_clean_install_harness.py` (stub aws/ssh/scp).

Verification: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q` →
**3137 passed**; after rebase `tests/test_clean_install_harness.py
tests/test_packaging.py` → 34 passed (only Coga state came in upstream).

Unverified assumptions (the real run confirms them): EC2 Mac AMIs ship CLT
and Homebrew; `sysadminctl -addUser` works without secure-token prompts;
`amzn-ec2-macos-*` newest arm64 image boots on mac2.metal.

Next session (after unblock), from this checkout on the branch:
1. `export AWS_PROFILE=multiply-telemetry`; `aws-mac.sh preflight <region>`.
2. `COGA_CLEAN_INSTALL_ALLOCATE=yes aws-mac.sh provision mac1 <region> <az>`.
3. `walk mac1 pypi walk1` (expected stop at git/CLT), install CLT via VNC,
   `walk mac1 pypi walk2`, `walk mac1 main walk3`.
4. `teardown mac1`; host release only ≥24h after `HOST_ALLOCATED_AT` —
   `aws-mac.sh release mac1` the next day. Record every ID here and in the PR.
Fix any script bug the live run finds on the branch before bumping.

---

## Blockers

- [ ] [2026-09-30 14:24] [agent:claude] id=20260930T142425 Harness is pushed on branch macos-clean-install-harness; the required live provision→install→init→teardown cycle needs you to: (1) run 'aws sso login --profile multiply-telemetry' (token expired), and (2) approve allocating one mac2.metal dedicated host (24h minimum billing, release only after 24h) and name the region/AZ (suggest us-east-1; 'aws-mac.sh preflight <region>' shows quota and AZs). Then unblock and relaunch implement.
