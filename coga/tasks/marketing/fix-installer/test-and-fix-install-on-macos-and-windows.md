---
title: Test and fix install on macOS and Windows
status: active
owner: zach
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
contexts:
- coga/install
agent: claude
---

## Description

A human test, not an automated one. Zach (marketing) installs coga himself,
on a fresh macOS and a fresh Windows environment on his own hardware, the way
a first-time user would: follow the README / `coga/install` docs only, then
`uv tool install coga`, `coga init`, `coga build`, and a first `coga ticket`.
The agent session (run from Zach's usual coga checkout, not inside the fresh
environment) records every point where he gets stuck, confused, or has to
guess, and fixes what it can in the same session.

Known going in: on macOS, the Xcode Command Line Tools git stub and the
system Python 3.9 (below the 3.11 floor). Native Windows does not start at
all: `coga.git` imports `fcntl` at module top, so even `coga --help` fails,
and `repl_supervisor` / `megalaunch` need pty/termios/tty. The deep Windows
port is `make-coga-run-on-native-windows` (owner decision 2026-10-13); this
ticket feeds it findings and does not duplicate it.

Done when: both walks are done and their findings are listed per OS on the
blackboard (each tagged fixed-in-PR, tracked-elsewhere, or open); fixes that
fit this ticket are merged as PRs; and `docs/contexts/coga/install/SKILL.md`
matches what actually worked, including the fresh-environment setup below if
it proved useful.

## Context

### Getting a fresh machine (do this before the walk)

Zach's everyday accounts already have coga, uv and git state, so he must not
walk there. Pick option A per OS where possible; B is the fallback.

**macOS**

- **A. Fresh macOS VM (recommended; Apple Silicon only, free, ~1 h mostly
  download).** Install UTM from https://mac.getutm.app. Create a New Virtual
  Machine -> Virtualize -> macOS 12+ -> let it download the latest restore
  image (~15 GB) -> 4 CPU, 8 GB RAM, 64 GB disk -> start it and finish Setup
  Assistant (skip the Apple ID). This is a factory-new Mac: no Command Line
  Tools, no Homebrew, so the git stub and Python 3.9 issues show up for real.
  On an Intel Mac this is not possible; use B.
- **B. New user account (~5 min).** System Settings -> Users & Groups -> Add
  User -> Administrator, name `cogatest`. Log out, log in as `cogatest`.
  Clean home, PATH and caches, but machine-wide installs leak in: the Command
  Line Tools (so the git stub will NOT appear), Homebrew under `/opt/homebrew`
  (off PATH unless `/etc/paths.d` adds it), python.org Python in
  `/usr/local/bin`. Findings that depend on these get flagged.

**Windows (tester PC is Windows 11 Home: no Sandbox, no Hyper-V Manager)**

- **A. Fresh Windows 11 VM (free, ~1 h).** Install VirtualBox 7
  (https://www.virtualbox.org). Download the Windows 11 ISO from
  https://www.microsoft.com/software-download/windows11. New VM from the ISO,
  4 CPU, 8 GB RAM, 64 GB disk (VirtualBox 7 provides EFI + TPM 2.0). At the
  product-key screen choose "I don't have a product key" and pick Windows 11
  Home; it runs unactivated, which is fine for this. Sign in with any
  Microsoft account. If WSL2 is enabled on the host, VirtualBox runs slowly
  on top of it; that is expected.
- **B. New local user (~5 min).** Settings -> Accounts -> Other users -> Add
  account -> "I don't have this person's sign-in information" -> "Add a user
  without a Microsoft account" -> `cogatest`. Then Change account type ->
  Administrator. Sign out, sign in as `cogatest`. Leaks: Git for Windows,
  any "all users" Python, machine-wide winget packages.

**Record a baseline before installing anything** and paste it on the
blackboard, so findings can be told apart from leftovers:

- macOS (Terminal): `sw_vers; uname -m; xcode-select -p; which -a git python3
  brew uv coga claude gh`. Do NOT run `git --version` yet: on a fresh Mac it
  triggers the CLT install, which is itself the first finding to observe.
- Windows (PowerShell): `[Environment]::OSVersion; Get-ExecutionPolicy;
  Get-Command git,python,py,uv,coga,claude,gh,winget -ErrorAction
  SilentlyContinue | Format-Table Name,Source`.

### Walk rules

- Zach acts as a new user: docs only, no help from the agent unless he is
  stuck, and a needed hint is itself a finding.
- Per step, note: the exact command, what happened, what he expected, and
  how long he was stuck.
- Fix loop: finding -> PR -> merge -> re-walk the affected step in a fresh
  environment (VM snapshot taken right after the baseline, or a new user
  account).
- `coga/testing/clean-install/macos-aws` already covers the automated
  fresh-Mac harness on EC2; this ticket is the human counterpart and does not
  rent machines.
- Repo is public: no account IDs, emails or keys on the blackboard.

<!-- coga:blackboard -->
# Test and fix install on macOS and Windows

## Plan (2026-10-14, attended)

Human walk on Zach's own hardware in a fresh VM or fresh user account (see
Context). Steps: pick A/B per OS -> baseline -> walk macOS -> findings and
fixes -> walk Windows -> findings and fixes -> update `coga/install`.

## New-user walk: macOS

(not started)

## New-user walk: Windows

(not started)

## Carried-over finding

- This WSL checkout has 654 tracked files with CRLF in the worktree (index is
  LF; `core.autocrlf=input` hides it from `git status`). `aws-mac.sh` then
  fails `env: 'bash\r': No such file or directory`. Converted only
  `scripts/clean-install/{aws-mac.sh,run.sh,Dockerfile}` back to LF in place.
  Root cause unknown (likely a Windows-side git/editor touched the tree).
  Relevance to Windows users: a repo cloned with Windows git
  `core.autocrlf=true` would CRLF any shell scripts too; check whether coga
  ships/executes `.sh` or `ticket.py` with shebangs on that path.

## Blockers

- [x] [2026-10-14 13:19] [agent:claude] id=20261014T131919 Needs an attended session on Zach's own Mac and Windows machines: the ticket is a hands-on clean-install walk (uv tool install coga, coga init, coga build, first ticket) on those machines, which this queued Linux session cannot reach. Relaunch it attended on the Mac, then on Windows. The Windows fcntl port is tracked separately in make-coga-run-on-native-windows.
  resolved: [2026-10-14 16:45] [human:zach] Owner chose rented disposable AWS macOS and Windows hosts; the read-only Mac preflight is green, so the old own-machine attendance premise no longer blocks the ticket.

## Superseded designs

### 2026-10-14 — walk on rented AWS hosts (superseded same day)

Superseded because the ticket is a human test of a real user's experience;
the automated fresh-Mac case is already covered by
`coga/testing/clean-install/macos-aws`. No AWS host was allocated and no
money was spent; the SSO profile `coga-test` and the budget alert exist and
can be removed with the steps below.

The blackboard is a notepad to be written to often as the human and agent works through a task.

#### Session 2026-10-14 (megalaunch, Linux host)

- Nothing done yet. This ticket is a hands-on walk on Zach's own Mac and
  Windows machines with an attended agent there. A queued Linux session
  can't reach either machine, and writing per-OS findings without the walk
  would make them up.
- Known items are already tracked elsewhere and were not duplicated here:
  the Windows `fcntl`/pty port is in `make-coga-run-on-native-windows`; the
  Python <3.11 fail-loud is in `marketing/fix-installer/fail-loud-on-python-older-than-3-11`
  (blocked); the CLT stub doc is done (`coga/install` "macOS: install the
  Command Line Tools first").
- Next: run this ticket attended (`coga launch` from a coga checkout on
  Zach's Mac, then on the Windows box) and record findings per OS here.


#### Blockers

- [x] [2026-10-14 13:19] [agent:claude] id=20261014T131919 Needs an attended session on Zach's own Mac and Windows machines: the ticket is a hands-on clean-install walk (uv tool install coga, coga init, coga build, first ticket) on those machines, which this queued Linux session cannot reach. Relaunch it attended on the Mac, then on Windows. The Windows fcntl port is tracked separately in make-coga-run-on-native-windows.
  resolved: [2026-10-14 16:45] [human:zach] Owner chose rented disposable AWS macOS and Windows hosts; the read-only Mac preflight is green, so the old own-machine attendance premise no longer blocks the ticket.

#### Session 2026-10-14 (attended, Zach, WSL host) — supersedes the block premise

The blocker above assumed the walk must run on Zach's own machines. The owner
decided instead (see Decisions) to walk on rented fresh AWS machines, driven
from this WSL checkout, because his own machines already carry coga/uv/git
state and can't show a first-time user's experience. The ask is answered;
the owner can clear it with `coga unblock` before the next launch.

#### Decisions

- 2026-10-14: test on rented/disposable machines, not Zach's own (already has
  coga/uv/git state, so not a first-time user). macOS = EC2 Mac via
  `scripts/clean-install/aws-mac.sh`; Windows = Windows Sandbox if Pro, else
  EC2 Windows Server. Steps are logged below so Nico can review the method and
  it can be reproduced; promote the reproducible parts into the owning topics
  (`coga/testing/clean-install/macos-aws`, a Windows runbook) in the PR.
- Repo is PUBLIC: never record account IDs, emails, portal URLs, keys here.
- 2026-10-14 (owner): both OSes on rented AWS machines.
  - macOS: EC2 Mac via existing `aws-mac.sh` (fresh walk user per run, CLT
    removed). Known gap vs a retail Mac: Amazon's AMI ships Homebrew/AWS
    tooling; check `baseline.txt` that brew is not on the walk user's PATH.
  - Windows: EC2 Windows Server 2025 (option A), chosen over a Windows 11
    eval VM (B: faithful but ~1h setup) and Windows 11 Pro/Sandbox (C: USD 99;
    tester PC is Home). Known gaps vs a Windows 11 user, accepted by owner:
    no `python` Store-alias stub, ExecutionPolicy RemoteSigned (client is
    Restricted, blocks `Activate.ps1`), Store/winget/SmartScreen differ.
    Hard failures (fcntl/pty/termios) reproduce identically. Findings that
    hinge on those gaps get flagged "Server-only, unverified on Win11".
  - mac2 quota 1 approved 2026-10-14 (us-east-1).
- Fix loop (owner, 2026-10-14): walk -> note finding here -> fix PR ->
  merge -> re-walk in `main` mode (wheel from origin/main) on a new walk user
  on the same host. No unmerged-branch harness mode. To fit the 24h host
  window, line up same-day PR review with Nico before allocating; a fix that
  merges after the window is re-checked on the next rental (or the Windows
  day). Machine-wide first-run states (CLT prompt) are seen once per rental.
- Next: Mac walk (allocate host ~USD 15.60/24h min, owner go-ahead needed),
  then Windows walk. No Windows EC2 driver exists yet in
  `scripts/clean-install/`.

#### Test-path log (reproducible steps)

Two separate tracks; do not mix them:
- **Operator setup (A, B, ...)**: what the tester does once to get fresh
  machines (AWS login, CLI, harness). Never part of a coga user's path.
- **New-user walk (per OS)**: exactly what a first-time coga user does on the
  fresh machine. This is what findings and coga/install docs come from.

##### Operator setup A. AWS account access (one-time, console as root)
1. IAM Identity Center (top search "Identity Center"; NOT the "IAM" page).
   Region switcher (top right) -> US East (N. Virginia) us-east-1.
2. Enable -> "Enable with AWS Organizations".
3. Instance configuration: **Single-Region instance** (us-east-1). Why: the
   Multi-Region default creates a customer-managed KMS key (billed monthly);
   Single-Region uses an AWS-owned key (free). Not needed for a test account.
4. Dashboard appears ("successfully created the organization instance").
   Identity source: keep the default Identity Center directory (no action).
   Save the "AWS access portal URL" (`https://d-…awsapps.com/start` form)
   privately; `aws configure sso` asks for it.
5. Left sidebar -> Users -> Add user: username + own email, "Send an email to
   this user with password setup instructions"; skip groups; Add user.
   Accept the invite email, set password, register MFA.
6. Invite email ("invited you to AWS IAM Identity Center", expires in 7 days)
   -> Accept invitation -> set password -> register MFA (1Password).
7. Back in the root console, Identity Center -> Permission sets -> Create
   permission set -> Predefined -> AdministratorAccess -> Next (defaults,
   session 1 hour) -> Create.
8. Identity Center -> AWS accounts -> tick the account -> Assign users or
   groups -> Users tab -> the user -> Next -> AdministratorAccess -> Next ->
   Submit.
   Result: account page shows user -> AdministratorAccess; the access portal
   (signed in as the new user) lists the account after refresh.

##### Operator setup: cost guard and removal
- Cost so far: USD 0 (Identity Center, Organizations, permission sets, CLI,
  `aws configure sso`, `aws-mac.sh preflight` are all free).
- Spend happens only at: Mac host allocation (gated by
  `COGA_CLEAN_INSTALL_ALLOCATE=yes`; 24h min ~USD 15.60, then USD 0.65/h
  until *released* — a forgotten host is ~USD 475/month), and any Windows
  EC2 instance (cents/hour, plus its disk, until terminated).
- Guard: Billing and Cost Management -> Budgets -> Create budget -> template
  "Monthly cost budget", USD 25, email = own address. Alerts only; AWS has
  no hard spending cap. Check the EC2 console (Dedicated Hosts, Instances,
  Volumes) is empty after each session.
- Tester PC is Windows 11 Home 25H2 (build 26200): no Windows Sandbox, no
  Hyper-V. Windows walk needs EC2 Windows or a local VM instead.
- Removal: delete user + permission set, then Identity Center -> Settings ->
  Delete; AWS Organizations -> delete organization; `rm -rf ~/.aws` plus the
  CLI paths in B.

##### Operator setup B. Tester workstation (WSL Ubuntu, x86_64)
9. AWS CLI v2, user-local, no sudo (no `unzip` here, so Python extracts):
   ```sh
   d=$(mktemp -d) && cd "$d"
   curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
   python3 -I -c "import zipfile;zipfile.ZipFile('awscliv2.zip').extractall('x')"
   chmod -R u+x x/aws/install x/aws/dist
   x/aws/install -i ~/.local/aws-cli -b ~/.local/bin
   aws --version    # 2026-10-14: aws-cli/2.38.1
   ```
   Remove later: `rm -rf ~/.local/aws-cli ~/.local/bin/aws ~/.local/bin/aws_completer`.
10. `aws configure sso` (interactive): session name `coga`, start URL = the
    saved portal URL, region `us-east-1`, scopes default, approve in browser,
    pick the account + AdministratorAccess, CLI region `us-east-1`, output
    `json`, profile `coga-test`. Later logins: `aws sso login --profile coga-test`.


##### Operator setup C. Preflight (2026-10-14, read-only, USD 0)
11. `aws sso login` needs no TTY with `--use-device-code --no-browser`
    (`aws configure sso` fails under Claude Code's `!`: "Input is not a
    terminal"). Profile `coga-test` written by hand to `~/.aws/config`
    (`[profile coga-test]` -> `sso_session = coga`, account, role
    AdministratorAccess, region us-east-1; `[sso-session coga]` start URL,
    `sso_region`, `sso_registration_scopes = sso:account:access`).
12. `AWS_PROFILE=coga-test ./scripts/clean-install/aws-mac.sh preflight us-east-1`
    -> caller OK; **all mac2 dedicated-host quotas 0.0**; mac2.metal offered
    in us-east-1a/b/c/d; no existing hosts; newest AMI
    `amzn-ec2-macos-27.0-20260918-030202-arm64`.
    Next: request quota "Running Dedicated mac2 Hosts" = 1 (Service Quotas).
13. Quota request (console, us-east-1): Service Quotas -> Manage quotas ->
    type "EC2" in the AWS Services box -> Amazon EC2 -> View quotas -> search
    `mac2` -> select plain "Running Dedicated mac2 Hosts" (not m2/m2pro/
    m1ultra) -> Request increase at account level -> 1 -> Request. Submitted
    2026-10-14; track under Quota request history.

##### Operator-side finding (not a coga-user finding)
- This WSL checkout has 654 tracked files with CRLF in the worktree (index is
  LF; `core.autocrlf=input` hides it from `git status`). `aws-mac.sh` then
  fails `env: 'bash\r': No such file or directory`. Converted only
  `scripts/clean-install/{aws-mac.sh,run.sh,Dockerfile}` back to LF in place.
  Root cause unknown (likely a Windows-side git/editor touched the tree).
  Relevance to Windows users: a repo cloned with Windows git
  `core.autocrlf=true` would CRLF any shell scripts too; check whether coga
  ships/executes `.sh` or `ticket.py` with shebangs on that path.

#### New-user walk: macOS (fresh EC2 Mac)

(not started)

#### New-user walk: Windows (fresh EC2 Windows Server 2025)

(not started)

#### Handoff (implement, session 1, 2026-10-14) — attended, no branch yet

Done: operator setup A–C (AWS Identity Center login, CLI profile
`coga-test`, USD 50 budget alert, mac2 quota 1 approved, preflight OK);
decisions recorded above. No code changes, no branch, no spend on testing.
Not bumped: walks, fixes and the install-doc update are still to do.

Next session (owner plans tomorrow morning, Nico pre-warned for same-day PR
review):
1. `aws sso login --profile coga-test --use-device-code --no-browser`
   (run in background, give the owner the autofill URL); `export
   AWS_PROFILE=coga-test PATH=$HOME/.local/bin:$PATH`.
2. Owner go-ahead, then `COGA_CLEAN_INSTALL_ALLOCATE=yes
   ./scripts/clean-install/aws-mac.sh provision mac1 us-east-1 <az>` (try
   us-east-1a; on InsufficientHostCapacity try b/c/d). Note
   HOST_ALLOCATED_AT; schedule `release` reminder for +24h.
3. Check `baseline.txt`: is Homebrew on a new user's PATH?
4. `walk mac1 pypi walk1 <operator>` — expect stop at `git --version` (CLT).
   Record finding, then continue per the macos-aws runbook (headless CLT via
   softwareupdate, new walk user), attended agent login, `coga build`, first
   ticket. Re-create CLT-missing state with `macos-walk.sh reset` when
   re-testing a CLT fix.
5. Fix loop: finding -> PR -> merge -> `walk mac1 main walkN`.
6. `teardown mac1` same day; `release mac1` after 24h (stops billing).
Then the Windows day (no driver yet: manual console launch logged step by
step, or build `aws-windows.sh` — owner undecided).

#### Session 2026-10-14 (attended, Zach, resumed)

- Confirmed the AWS SSO session is active and reran the read-only macOS
  preflight from the WSL checkout. Quota remains 1; `mac2.metal` is offered
  in us-east-1a/b/c/d; there are no existing `mac2.metal` hosts; and the
  newest arm64 AMI remains
  `amzn-ec2-macos-27.0-20260918-030202-arm64`.
- Confirmed the three harness files repaired in session 1 are plain LF/ASCII
  in this worktree. No AWS resource was created and spend remains USD 0.
- The next mutating step is still the explicitly gated Mac host allocation.
  Do not run it until Zach approves the roughly USD 15.60 / 24-hour minimum
  recorded above and Nico is available for the same-day fix/review loop.
