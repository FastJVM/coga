---
title: Affordable macOS testing on owned Macs and per-minute CI
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
step: 3 (open-pr)
agent: claude
launch_generation: f780d6a3-de29-44c3-a205-a4035f1517d7
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

## Dev

branch: owned-mac-clean-install

Plan (implement, 2026-10-06): #943 merged (76ed1c43d), so build on main.
#968 (Python 3.11 pin, open) edits only the `walk` hunk of macos-walk.sh and
container.sh; stay out of those hunks so the owned path inherits the pin.
- Factor aws-mac.sh's walk/evidence/vnc/ssh helpers into a sourced
  `scripts/clean-install/mac-common.sh`; add `owned-mac.sh` (SSH driver):
  `vm` = disposable Tart vanilla VM on Apple Silicon reached by ProxyJump
  (vanilla image has no CLT, admin/admin, NOPASSWD sudo); `attach` = ordinary
  host (Intel compat), never reset, needs a dedicated test account with
  passwordless sudo; `cleanup` deletes VM or walk users.
- Gate macos-walk.sh `reset` and `vnc` on a disposable marker that only a
  driver-created target (EC2 instance, cloned VM) receives.
- New topic coga/testing/clean-install/macos-owned (+ twin, packaging list):
  setup/reset/cleanup, costs, hosted-CI comparison + recommendation.

## Handoff (implement, 2026-10-06)

Commit dcaedc01f on `owned-mac-clean-install` (pushed, rebased on origin/main).

What changed:
- `scripts/clean-install/owned-mac.sh` (new): `preflight SSH_HOST`;
  `vm NAME SSH_HOST [IMAGE]` (arm64 only; `tart clone` of
  `ghcr.io/cirruslabs/macos-tahoe-vanilla:latest` → `tart run --no-graphics`
  → `tart ip`; admin/admin used once via SSH_ASKPASS to install a per-run
  key; later calls ProxyJump through the Mac; designate-disposable + reset);
  `attach NAME SSH_HOST` (ordinary Mac, needs `sudo -n`, baseline only, never
  resets, no vnc); `walk`, `ssh`, `vnc` (VM only), `status`, `cleanup`
  (VM: tart stop/delete; host: delete recorded walk users + /tmp scripts;
  idempotent via resources.env).
- `scripts/clean-install/mac-common.sh` (new, sourced): run/record/checksum/
  mac/copy_walk_scripts/mac_walk/fetch_evidence/mac_vnc moved out of
  aws-mac.sh unchanged in behavior; aws-mac.sh now sources it and calls
  `designate-disposable` before `reset`.
- `macos-walk.sh`: new `designate-disposable RUN` writes
  `/etc/coga-disposable-test-mac`; `reset` and `vnc` refuse without it; vnc
  sets the current user's password (was hardcoded ec2-user). Did NOT touch
  the `walk` hunk that open PR #968 (Python 3.11 pin) edits — expect a clean
  merge either order; owned path inherits the pin.
- Docs: new topic `coga/testing/clean-install/macos-owned` (+ packaged twin,
  added to REQUIRED_BOOTSTRAP_CONTEXT_REFS); links from coga/testing,
  clean-install, macos-aws (+ twins); dated
  `docs/evidence/macos-install-test-costs.md` (indexed in docs/README.md).

Rates re-verified 2026-10-06: AWS price list (published 2026-09-25) mac2
USD 0.65/h (24h min USD 15.60), mac1 Intel USD 1.083/h; GitHub standard
macOS USD 0.062/min, free for public repos (FastJVM/coga is PUBLIC), labels
macos-15/26 arm64 + macos-15-intel/26-intel, passwordless sudo, no built-in
interactive access; Buildkite M4 Medium USD 0.12/min, needs Pro USD 30/active
user/month (Free has no macOS), Apple silicon only, Xcode+Homebrew
preinstalled, terminal/desktop access. Tart free ≤100 host cores/personal.
Recommendation (in evidence page): owned Apple-silicon VM is the default for
fresh-install + attended evidence; Intel attach for x86_64 compat only; EC2
optional; hosted CI only for an automated install/init/validate smoke on
GitHub Actions (free here) — needs explicit owner decision (no-CI posture);
no workflow was added.

Verification:
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q` → 1 failed, 3279
  passed. The failure,
  `tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`,
  fails identically on a clean origin/main worktree (index 0:
  'coga/recurring/autoclose-merged/ticket.py' vs
  'coga/recurring/_custom-phone-home/ticket.py' — looks dependent on the live
  repo's coga/recurring listing). Pre-existing, unrelated; not fixed here.
- `tests/test_packaging.py tests/test_clean_install_harness.py` → 47 passed
  (5 new owned-Mac/marker regressions; AWS tests pass on the refactor).
- `env -u SLACK_WEBHOOK_URL coga validate --json` → 0 errors (28 unrelated
  warnings on other tickets).

Not done / open:
- No owned-Mac live run: the owner has not supplied SSH access to either
  spare Mac. Untested live assumptions: `tart run` over SSH without a GUI
  session, SSH_ASKPASS password bootstrap through ProxyJump, image download
  size. Run `owned-mac.sh preflight/vm/walk/cleanup` when access exists and
  record results here.
- AWS host h-0833c01ac15e645ac release belongs to PR #943's ticket; not
  touched, no AWS resources allocated.

## Peer review

Completed 2026-10-06. `codex review --base main` **returned** with two
must-fix findings: P1 cleanup could delete a pre-existing account after a
rejected walk; P2 failed SSH checks could falsely record an account as deleted.
The initial sandbox invocation could not initialize its app-server; the
authorized unsandboxed retry returned normally. Review transcript:
`/tmp/owned-mac-peer-review.txt` (local, ephemeral).

Fixed both: attached runs give newly created accounts a per-run ownership
tag; deletion requires a match and confirms absence on the Mac. Transport or
account-check failures leave cleanup retryable. Added regressions for an
existing account, changed ownership, failed walks after account creation,
SSH failure, and account checks failing before or after deletion. Attached
runs also own separate script directories; fresh users can read the copied
wheel and execute the shared scripts. Owning topic and packaged twin updated.

`codex review --uncommitted` **returned** after those fixes. Its one P2 finding
was that mode 644 contradicted the documented direct script invocation;
restored mode 755 and verified the focused suite again. No findings remain
unaddressed. Follow-up transcript: `/tmp/owned-mac-fixes-review.txt`.

Verification on the final branch:
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q` -> **3285 passed**
  in 258.52s after rebasing onto `c93ced159`. The earlier implementation
  handoff's legacy-adoption failure did not recur. Receipt:
  `/tmp/owned-mac-rebased-pytest.txt`.
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_clean_install_harness.py tests/test_packaging.py -q`
  -> **52 passed**.
- `env -u SLACK_WEBHOOK_URL PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --task marketing/fix-installer/affordable-macos-testing-on-owned-macs-and-per-min --json`
  -> **1 OK, no issues**.
- `bash -n` individually for all six `scripts/clean-install/*.sh` files;
  `git diff --check main...HEAD` -> clean.
- `python3 /tmp/owned-mac-tty-check.py` in a real PTY at 80x24 and 120x40:
  `owned-mac.sh ssh` retained terminal stdin/stdout, passed `-t` and the
  attended `sudo -iu walk1` command, and did not pipe output to `host.txt`.
  SSH was stubbed; this verifies local terminal forwarding only. No live Mac,
  VM boot, agent login, or VNC claim is made without owner-supplied SSH access.

Reconfirmed #943 merged and #968 remains open; the cleanup tag addition is
above its uv/Python walk changes. GitHub and Buildkite pricing pages still
support the comparison. No paid service, CI workflow, or AWS allocation added.

Pushed `owned-mac-clean-install` with `--force-with-lease`, tip `941702e8e`
(implementation `3014627ed`, review fixes `941702e8e`), two commits ahead of
current main. Returned to clean `main` before writing this handoff.
Live owned-Mac execution remains conditional on the owner supplying SSH access;
the separate AWS release work remains outside this ticket.

## PR

Add an SSH driver for inexpensive macOS install testing: disposable Tart
VMs on owned Apple Silicon Macs for fresh installs, and attached Intel Macs
for compatibility checks. Reuse the AWS harness's PyPI/fetched-main wheel
walk and evidence collection, confine reset and VNC password changes to
designated disposable targets, and require per-run account ownership before
attached-host cleanup. Failed cleanup checks remain retryable.

Document setup, reset, attended continuation, cleanup, and the dated
GitHub Actions/Buildkite/EC2 cost comparison in the testing topics and their
packaged twins. Hosted CI remains a recommendation requiring an owner decision;
this change adds no workflow or paid service. Live owned-Mac testing awaits
owner-provided SSH access.

Test plan: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q` (3285 passed);
`PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_clean_install_harness.py tests/test_packaging.py -q`
(52 passed); task-scoped source CLI validation (1 OK, no issues); shell syntax
and diff checks; real PTY forwarding checks at 80x24 and 120x40 with stubbed SSH.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `marketing/fix-installer/affordable-macos-testing-on-owned-macs-and-per-min`
Recorded: 2026-10-07T18:28:15+00:00

    Branch 'owned-mac-clean-install' is not safe to publish. refs/heads/owned-mac-clean-install does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase origin/main`. Reconcile it and relaunch, or `coga block --task marketing/fix-installer/affordable-macos-testing-on-owned-macs-and-per-min`.
