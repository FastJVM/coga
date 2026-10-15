---
title: Windows EC2 test harness
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
step: 2 (peer-review)
agent: claude
---

## Description

Build the Windows counterpart of the macOS EC2 clean-install harness so an
agent can rent a fresh native Windows machine, drive it over SSH, and throw it
away. It is the test bed for the sibling ticket
`windows-native/core-port-cli-and-test-suite-pass-on-native-window` and its
siblings, which run their
fix loop and acceptance checks on this box. This ticket builds the harness
only. It does not port Coga, so a walk is expected to stop at
`coga --version` with the `fcntl` import error.

Deliverables:

- `scripts/clean-install/aws-windows.sh`, the host-side driver, modeled on
  `aws-mac.sh`. Subcommands: `preflight REGION` (read-only),
  `provision NAME REGION [AZ]`, `walk NAME pypi|main USER`,
  `ssh NAME [CMD…]`, `checkout NAME REF`, `rdp NAME`, `status NAME` and
  `teardown NAME`.
- A PowerShell walk script that runs as a new local user on the box and does
  the same steps as `container.sh`:
  1. `whoami`, then `git --version`;
  2. install uv with its official installer and run `uv python install 3.11`
     first; only then export `UV_PYTHON=3.11` and
     `UV_PYTHON_DOWNLOADS=never`. Setting `never` before the install blocks
     it, and the macOS walk uses the same order;
  3. `uv tool install` Coga from PyPI or from the `main` wheel;
  4. `coga --version`;
  5. `git init`, then `coga init --user <operator>`;
  6. `coga validate --json`.

  It records a transcript, the first failing step and its exit code.
- `checkout NAME REF` clones the public repo at a given branch or SHA on the
  box, then runs `uv sync --extra test`. This is what the port's fix loop
  uses. `ssh NAME <cmd>` must run a command there and return its exit code.
  The fix loop runs as the SSH admin account in its own work directory, and
  provision installs uv and Python 3.11 for that account. Walk users are
  always new local users, so a fix-loop install never leaks into a walk:
  `uv tool install` is per user.
- A runbook topic, `coga/testing/clean-install/windows-aws`. It covers cost,
  credentials, provision, walk, the fix-loop helpers, RDP and teardown. Link
  it from the parent `coga/testing/clean-install` topic.

### Acceptance

The ticket is done when one real run on the `coga-test` profile does all of
the following, and the PR reports the instance ID, AMI and its name, region,
the walk result, and the teardown time:

1. preflight, then provision a Windows Server 2025 instance;
2. SSH in;
3. `checkout main`, and a remote `python -c "import sys; print(sys.platform)"`
   prints `win32`;
4. a `walk` records its first failure at `coga --version` (expected:
   `fcntl`);
5. `rdp` retrieves the admin password and prints a working tunnel command.
   An agent can't look at a desktop, so the owner confirms that a desktop
   session opens during the `review` step;
6. `teardown` leaves nothing billing, confirmed by `status` and
   `aws ec2 describe-instances`.

The runbook and its packaged twin also pass `tests/test_packaging.py`.

## Context

### Machine on file

- Use the AWS account behind SSO profile **`coga-test`** in **us-east-1**.
  Log in with `aws sso login --profile coga-test` (add
  `--use-device-code --no-browser` on a headless host), then
  `export AWS_PROFILE=coga-test`.
- The profile, the USD 50 monthly budget alert and the choice of
  **EC2 Windows Server 2025** come from the `marketing/fix-installer`
  installer ticket's AWS setup. The owner accepted its known gaps against a
  Windows 11 desktop user.
- Never use root credentials. The repo is public, so never write account
  IDs, emails, keys or passwords into tickets, logs or the PR.

### Cost gate

- Windows EC2 bills per second, with no dedicated host and no 24-hour
  minimum, so it is far cheaper than the Mac (cents per hour plus the EBS
  disk until termination).
- Still keep an explicit opt-in like `COGA_CLEAN_INSTALL_ALLOCATE=yes`, and
  ask the owner before the first real provision.
- Owner decision 2026-10-14: after the owner approves the first provision,
  agents may provision and tear down Windows instances for the
  `windows-native/` tickets without asking again, as long as every session
  ends with teardown. Record this rule in the runbook.
- Write every resource ID to `.coga/clean-install/<name>/resources.env`
  (gitignored) as soon as it exists, so a failed provision can still be torn
  down, and make `teardown` safe to rerun.

### Design pointers

- Pattern to copy: `scripts/clean-install/aws-mac.sh` and the runbook
  `coga/testing/clean-install/macos-aws`
  (`docs/contexts/coga/testing/clean-install/macos-aws/SKILL.md`). The
  runbook is cited, not attached. Read its Provision, Walk and Teardown
  sections. Reuse:
  - the key-pair and `/32` SSH security-group setup;
  - the ID ledger and the evidence directory layout;
  - building `main` mode from the fetched `origin/main`, never the working
    tree.
- Windows Server 2025 ships OpenSSH Server as an optional capability.
  Enable and start it, open the firewall, and install the public key for the
  administrator from EC2 user data (`<powershell>` block). Pick the AMI by
  name filter (`Windows_Server-2025-English-Full-Base-*`), newest first, and
  let `COGA_WIN_AMI` pin it.
- Install Git for Windows during provision so the walk exercises Coga, not
  a missing git. Record the baseline (OS build, git, Python, PowerShell
  version) to `baseline.txt` the way the Mac harness does.
- RDP: fetch the admin password with `ec2 get-password-data` and the
  key-pair private key, and reach port 3389 only through an SSH tunnel. Never
  open 3389 in the security group. The port ticket needs a real console for
  its attended `coga launch` check.
- The new topic is a packaged twin. Put it in both
  `docs/contexts/coga/testing/clean-install/windows-aws/SKILL.md` and
  `src/coga/resources/templates/coga/bootstrap/contexts/…`, and add the ref
  next to `coga/testing/clean-install/macos-aws` in
  `tests/test_packaging.py`'s required bootstrap context refs.
  `coga/packaging` owns the twin rule.

### Gotchas carried over

- This WSL checkout has had CRLF in tracked files, so `aws-mac.sh` failed
  with `env: 'bash\r'`. Make sure the new `.sh` and `.ps1` files are LF in
  the index. Consider a `.gitattributes` rule for `*.sh text eol=lf`.
- Out of scope: porting Coga itself (the sibling ticket), the human walk
  (`marketing/fix-installer/test-and-fix-install-on-macos-and-windows`), and
  changes to `coga/install`.
- This ticket absorbs the parked draft `_v2/windows-native-clean-install`,
  which was deleted when this subproject was created. That draft's Windows
  install baseline for `coga/install` moved to
  `windows-native/interactive-coga-launch-on-native-windows`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: windows-ec2-harness

Plan (agreed with owner 2026-10-15): `aws-windows.sh` modeled on `aws-mac.sh`
plus `windows-walk.ps1` (PowerShell 5.1; modes setup/baseline/adduser/walk/checkout).
RSA key pair (get-password-data needs RSA). User data only enables sshd + admin key;
git, uv, Python 3.11 for Administrator and baseline over SSH. Remote default shell
stays cmd.exe so `ssh NAME CMD` returns the real exit code. Walk users log in over
SSH with a generated password via SSH_ASKPASS. t3.large + 50 GB gp3 default.
Owner approved the first provision (2026-10-15). AWS: `coga-test` profile to be
added on the existing `fastjvm` SSO session (owner's suggestion).

## Implement handoff (2026-10-15)

Pushed `windows-ec2-harness` (one commit, 47aa80b, rebased on origin/main da4b043).
Added: `scripts/clean-install/aws-windows.sh` (preflight, provision, walk, ssh,
checkout, rdp, status, teardown), `scripts/clean-install/windows-walk.ps1`
(baseline, setup, adduser, checkout, walk), runbook
`coga/testing/clean-install/windows-aws` + packaged twin, links from
`coga/testing`, `coga/testing/clean-install`, `docs/README.md`, the ref in
`REQUIRED_BOOTSTRAP_CONTEXT_REFS`, and `.gitattributes` (`*.sh`, `*.ps1` eol=lf).

### Acceptance run (profile coga-test, us-east-1a, t3.large)

- Run `win3`: instance i-06124f3a45bd17aba, AMI ami-00d8aa800578d8b12
  (Windows_Server-2025-English-Full-Base-2026.09.17), launched 18:31:26Z,
  SSH up ~2 min after launch. Baseline: Server 2025 Datacenter 24H2 build
  26100.33451, PowerShell 5.1; after setup Git 2.56.0.windows.2
  (system core.autocrlf=true), uv 0.13.1, Python 3.11.17 for Administrator.
- `checkout win3 main` cloned + `uv sync --extra test` OK; remote
  `python -c "import sys; print(sys.platform)"` printed `win32`;
  `ssh win3 cmd /c "exit 7"` returned 7.
- Walks: `walk3` (pypi) and `walk5` (main wheel coga-0.4.1 from origin/main
  78a0e74): every step PASS through `uv tool install`, then
  `FAIL (exit 1) coga --version` — `ModuleNotFoundError: No module named 'fcntl'`
  at `coga/git.py` `import fcntl`. walk5's host ssh stream died on a VPN exit
  change; the walk finished on the box and evidence was fetched afterwards.
- `rdp win3`: admin password decrypted (saved locally only); through the printed
  tunnel, localhost:13389 returned an RDP X.224 Connection Confirm (NLA offered).
  **Owner still to confirm a desktop session opens (review step; needs a fresh
  provision — box is gone).**
- Teardown: win3 terminated 19:13:05Z, SG and key pair deleted. `status` shows
  terminated, no tagged volumes; `describe-instances` shows win1/win2/win3 all
  terminated; no harness SGs, key pairs or volumes remain.

### Bugs found and fixed during the run

- win1: never reachable. Server 2025's built-in `OpenSSH-Server-In-TCP` firewall
  rule exists but isn't usable; user data now enables it for all profiles.
- win2: owner's Surfshark VPN exits from several addresses, so the `/32` SG rule
  matched intermittently. Added `COGA_WIN_SSH_FROM` (CIDR override; owner chose
  this over disconnecting the VPN). Mid-run the VPN moved to another exit range;
  that range was added manually to win3's SG (noted in host.txt).
- Default `sshd_config` has `AllowGroups administrators "openssh users"`; walk
  users are now added to OpenSSH Users (documented in the runbook).
- `as_user` put ssh options after the remote command (hung on host-key prompt);
  fixed. Added ServerAliveInterval keepalives so a dead route fails, not hangs.
- `repo_url` failed on an origin URL with a trailing slash; fixed.

### Notes for next steps

- Host setup: `coga-test` profile was added to `~/.aws/config` on the `fastjvm`
  SSO session (the session has one account; same as multiply-telemetry).
- Adjacent (not fixed, out of scope): `aws-mac.sh` has the same `/32`-behind-VPN
  weakness and no SSH keepalives.
- Review not yet run; design approval is not code review.

## PR

```yaml
title: Add the Windows EC2 clean-install harness
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5); see implement handoff.
head: 47aa80b1619aa500de664e14084eed70fa9d1f2d
base: da4b0436266a5ce1039c4017765b0fd75bd03b5c
depth: deep
rationale: New paid-cloud tooling (provisioning, credentials, network exposure) with no independent review yet; its correctness is shown by a live run rather than tests.
implementation: aws-windows.sh drives AWS and SSH from the host (ledger, /32 or COGA_WIN_SSH_FROM SSH rule, RSA key, Server 2025 user data enabling sshd), windows-walk.ps1 runs baseline/setup/adduser/checkout/walk on the box under PowerShell 5.1; the windows-aws runbook and twin document cost, approval rule, provision, walk, fix loop, RDP and teardown.
deviations: Added COGA_WIN_SSH_FROM (owner-approved) because the owner's VPN exits from a range; walk users join OpenSSH Users because Windows' default sshd_config restricts logons to that group.
limitations: The owner has not yet confirmed an RDP desktop session (only an RDP protocol handshake through the tunnel was verified). The PowerShell script has no automated test; it was exercised on the live box only.
files:
  .gitattributes: Keep *.sh and *.ps1 LF so the scripts run from CRLF-prone checkouts.
  scripts/clean-install/aws-windows.sh: Host-side driver for the Windows harness.
  scripts/clean-install/windows-walk.ps1: Box-side baseline, setup, user creation, fix-loop checkout and walk.
  docs/contexts/coga/testing/clean-install/windows-aws/SKILL.md: New runbook topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/clean-install/windows-aws/SKILL.md: Packaged twin of the runbook.
  docs/contexts/coga/testing/clean-install/SKILL.md: Link the Windows harness from the parent topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/clean-install/SKILL.md: Twin of the parent-topic link.
  docs/contexts/coga/testing/SKILL.md: Link the Windows harness from coga/testing.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/SKILL.md: Twin of the coga/testing link.
  docs/README.md: Index the new runbook.
  tests/test_packaging.py: Require the windows-aws bootstrap context ref.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Review belongs to the next workflow step; not yet run.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: 47aa80b1619aa500de664e14084eed70fa9d1f2d
    base: da4b0436266a5ce1039c4017765b0fd75bd03b5c
    detail: 3669 passed.
  - command: AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh preflight/provision/checkout/ssh/walk/rdp/teardown/status (run win3)
    status: passed
    head: 47aa80b1619aa500de664e14084eed70fa9d1f2d
    base: da4b0436266a5ce1039c4017765b0fd75bd03b5c
    detail: Live run on uncommitted script versions whose content equals the commit's for the box script; driver gained keepalives and the trailing-slash fix during the run (both exercised after the change). win32 printed; walks failed at coga --version (fcntl) as expected; teardown left nothing billing.
```
