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
step: 1 (implement)
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
