---
title: macOS clean-install harness on AWS
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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/943
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

## Live run mac1 — 2026-09-30 (claude, megalaunch)

Owner approved one mac2.metal host in us-east-1. Branch now has a second
commit (`1935e3d48`) with fixes found live. Full suite 3137 passed before the
fix; harness + packaging tests 34 passed after.

Resources (all in `.coga/clean-install/mac1/resources.env`, account 758808001216):
- Host `h-0833c01ac15e645ac` us-east-1a, allocated 2026-09-30T23:28:57Z —
  **STILL ALLOCATED AND BILLING.** AWS refused release until
  2026-10-01T23:28:57Z. Run `AWS_PROFILE=multiply-telemetry
  scripts/clean-install/aws-mac.sh release mac1` after that (needs the
  local `.coga/clean-install/mac1/` from this checkout, or
  `aws ec2 release-hosts --host-ids h-0833c01ac15e645ac --region us-east-1`).
- Instance `i-0c94f48cbd0210aa0` (3.235.126.9) terminated 23:50:28Z.
- SG `sg-01259984f101c8d33` deleted; key pair `coga-clean-install-mac1` deleted.
- AMI `ami-0531fecfb292182a3` (amzn-ec2-macos-27.0-20260918-030202-arm64).

Walks:
- walk1 (pypi): stopped at `git --version` — over SSH: "No developer tools were
  found and no install could be requested (possibly because there is no active
  GUI session)". Expected CLT finding. CLT then installed headlessly via
  `softwareupdate -i "Command Line Tools for Xcode 27.0-27.0"` (not the GUI
  dialog; VNC path not exercised).
- walk2: harness bug — sysadminctl refused duplicate full name but exit 0.
  Fixed (per-user full name + `id` check).
- walk3 (pypi): `uv tool install coga` → PyPI `coga==0.0.1`, "No executables
  are provided by package `coga`" (exit 2). **Installer finding for
  run-clean-installs-and-file-issues** (PyPI name holds a stub, not Coga).
- walk4 (main wheel `coga-0.3.2`, origin/main `375df29ab`, sha256
  46387d98…aa9d2d): install, `coga init`, `coga validate` all PASS.

Assumptions checked: AMI ships CLT + Homebrew (yes); sysadminctl works without
secure-token prompts (yes); newest arm64 AMI boots on mac2.metal (yes, SSH in
~5 min). New: CLT receipts sit under SIP in
`/Library/Apple/System/Library/Receipts` and cannot be forgotten; they did
not stop softwareupdate offering CLT. Runbook updated.

Next (open-pr): put these IDs/outcomes in the PR description; note the host
release is pending until 2026-10-01T23:29Z.

## Blockers

- [x] [2026-09-30 14:24] [agent:claude] id=20260930T142425 Harness is pushed on branch macos-clean-install-harness; the required live provision→install→init→teardown cycle needs you to: (1) run 'aws sso login --profile multiply-telemetry' (token expired), and (2) approve allocating one mac2.metal dedicated host (24h minimum billing, release only after 24h) and name the region/AZ (suggest us-east-1; 'aws-mac.sh preflight <region>' shows quota and AZs). Then unblock and relaunch implement.
  resolved: [2026-09-30 16:28] [human:nicktoper] Owner re-ran aws sso login for multiply-telemetry (sts identity verified 2026-09-30) and approved allocating one mac2.metal dedicated host in us-east-1 (24h minimum billing); AZ to be chosen from preflight output.

## Peer review

`codex review --base main` **returned** on 2026-09-30. It found two P2
issues: generated walk/VNC passwords appeared in command traces, and the
host-side main-wheel path required GNU `sha256sum`. Both are fixed: the
password-bearing calls bypass tracing, new evidence is owner-readable only,
and wheel checksums fall back to `shasum -a 256`.

Manual review also found that `record KEY "$(aws ...)"` masked AWS failures.
Resource output is now captured with its exit status before recording; failed
identity/SG/host/instance calls stop without recording an empty ID or launching
later resources. Regression tests cover those failures, secret-free traces,
and a main-wheel walk with no `sha256sum` on PATH. The runbook and packaged
twin document the behavior.

Verification:
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/test_clean_install_harness.py tests/test_packaging.py`: 40 passed.
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q`: 3143 passed
- `bash -n scripts/clean-install/aws-mac.sh scripts/clean-install/macos-walk.sh scripts/clean-install/container.sh` and `git diff --check`: passed.
- Drove the SSH wrapper and Mac ticket continuation in real PTYs at 80x24 and
  120x40, using local SSH/agent substitutes. Prompts displayed, typed input
  arrived, the multiword title stayed intact, and both runs recorded
  `ticket_exit_code=0`. This checks terminal plumbing, not live agent login.
- Read the saved mac1 resource ledger and walk1/walk3/walk4 receipts to verify
  the implementation handoff. No AWS resources created during review; VNC,
  agent authentication and a real first ticket remain unexercised.

Rebased unconditionally onto fetched main, fixed the findings, and pushed
with `--force-with-lease` (tip `69895a555`). Returned to clean main before writing this handoff.
Host release is still pending; the earliest release time is
2026-10-01T23:28:57Z. Keep that outstanding operation visible in the PR.

Resume verification — 2026-09-30: completed the checkout start check on clean
`main` at `459800ff6`; verified the remote feature branch still points to
reviewed tip `69895a55583202d791892d571aba14af2ff0a6ea`. Changes on main
since the recorded rebase are Coga state only. The returned review, fixes,
test receipts, and PR body above remain current; no code or AWS changes
were needed in this resumed session. Advancing the completed peer-review
step; delayed host release remains outstanding.

Handoff resumed 2026-10-01T04:30Z: start check passed on clean, fetched
`main`. Verified GitHub's feature branch still points to reviewed commit
`69895a55583202d791892d571aba14af2ff0a6ea`; restored its missing local
tracking branch. Upstream changes since the recorded rebase are exclusively
Coga task/log state, so the returned review and test evidence above still
apply. No code changed or AWS resources created in this resumed handoff.

## Open-PR verification

The first `coga open-pr` refused because upstream included a README change.
Rebased onto fetched `origin/main` without conflicts; `git range-diff`
confirmed all three reviewed patches unchanged. Re-ran
`PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q`: 3143 passed in 276.43s;
`git diff --check` passed. Pushed tip `d2cf99bc1` with an explicit lease
against reviewed tip `69895a555` and returned to clean, current `main`.
The returned review remains applicable. Host release remains outstanding as
documented below; no AWS operations were performed in this step.

## PR

Adds an EC2 Mac clean-install harness for the current PyPI release and wheels
built from fetched `origin/main`. It provisions a `mac2.metal` dedicated host,
records resource IDs for cleanup, removes the AMI's Command Line Tools to
expose the fresh-Mac Git prerequisite, and runs the Linux harness's shared
install/init/validate script as a new macOS user. The runbook covers spend
approval, region/quota checks, SSH/VNC continuation, and delayed host release.
Provisioning stops on failed AWS calls; generated passwords stay out of
command traces; wheel checksums support Linux and macOS operators.

Live cycle, 2026-09-30, owner-approved AWS profile `multiply-telemetry`:
- Region/AZ: `us-east-1` / `us-east-1a`.
- Host: `h-0833c01ac15e645ac`, allocated `2026-09-30T23:28:57Z`.
- Instance: `i-0c94f48cbd0210aa0`, terminated `2026-09-30T23:50:28Z`.
- AMI: `ami-0531fecfb292182a3` (`amzn-ec2-macos-27.0-20260918-030202-arm64`).
- Security group `sg-01259984f101c8d33` deleted `23:50:29Z`; key pair
  `coga-clean-install-mac1` deleted `23:50:30Z`.
- Initial PyPI walk stopped at `git --version` without CLT. CLT was then
  installed headlessly; the GUI prompt/VNC path was not exercised.
- PyPI retry resolved `coga==0.0.1` and failed at `uv tool install coga`
  because the package provides no executables (exit 2).
- Main wheel `coga-0.3.2`, source `375df29abed60dcdc426daba7a5148aa1a9321bf`,
  SHA-256 `46387d984e8cea33201f7c4924808266ce6a06e29b2d00e7b27f6025c8aa9d2d`:
  install, `coga init`, and `coga validate --json` all passed.
- Agent login and a real first ticket were not run. Installer findings belong
  to `marketing/fix-installer/run-clean-installs-and-file-issues`.

**Cleanup remains incomplete: the host is still allocated and billing.** AWS
refused release within its 24-hour minimum. At or after
`2026-10-01T23:28:57Z`, once the host is available, run
`AWS_PROFILE=multiply-telemetry scripts/clean-install/aws-mac.sh release mac1`
from the checkout retaining `.coga/clean-install/mac1/`, or
`aws --profile multiply-telemetry --region us-east-1 ec2 release-hosts --host-ids h-0833c01ac15e645ac`.
Confirm release and record its time before considering cleanup complete.

Test plan: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q`: 3143 passed; focused harness/packaging suite (40 passed),
Bash syntax and diff checks, terminal continuation at 80x24 and 120x40 with
transport/agent substitutes, plus the recorded EC2 Mac install/init cycle.
