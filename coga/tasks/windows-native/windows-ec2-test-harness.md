---
title: Windows EC2 test harness
status: done
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
- A runbook skill, `coga/testing/clean-install/windows-aws`. It covers cost,
  credentials, provision, walk, the fix-loop helpers, RDP and teardown. Link
  it from the parent `coga/testing/clean-install` skill.

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
  (`coga/skills/coga/testing/clean-install/macos-aws/SKILL.md`). The
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
- The skill has a packaged twin. Put it in both
  `coga/skills/coga/testing/clean-install/windows-aws/SKILL.md` and
  `src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md`.
  `tests/test_packaging.py` checks the twin and required wheel resources.
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

pr: https://github.com/FastJVM/coga/pull/1026
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
- Review findings and verification are recorded below.

## Peer review

**Completed — Codex direct review, 2026-10-15 (local).** Final head
`a12cf28fde18ef4f4f430e3bd56065725550f6e7`, base
`6f2316b71821fb181a3aa49f47339b91e0ad33f6`. No nested reviewer CLI ran.
Codex independently reviewed Claude's implementation, then implemented and
self-reviewed the owner-approved fixes. The final fixes have no independent
review receipt; recommend **deep**. No unresolved must-fix findings remain.

Two findings fixed:

- cmd.exe interpreted unquoted argv such as `a&b`, `a>b`, and `%PATH%`.
  Encoded PowerShell now starts executables directly with CRT quoting and
  explicitly forwards their exit codes. An explicit `cmd /c` line retains
  shell parsing, including its embedded quotes.
- `Step` could mark a non-terminating cmdlet error PASS because LASTEXITCODE
  remained zero. Cmdlet ErrorRecords now fail the step; native stderr alone
  does not. The new regression cases run against real PowerShell 5.1.

The branch was rebased onto current main and pushed. Later main movement
through `fc2f267cf` touched only another ticket and the audit log; inspected it,
with no harness, test, or contract drift. All three changed context twins are
byte-identical; both new scripts are LF in the index. Final Linux suite:
`PYTHONPATH="$PWD/src" .venv/bin/python -m pytest -q -p no:cacheprovider`
→ **3673 passed, 5 skipped in 360.58s**, Python 3.12.12. The five Windows-only
cases passed on native Python 3.11.17 / PowerShell 5.1 (**5 passed, 1 deselected
in 29.19s**), using the current production script copied beside the tests,
without the repository conftest.

### Fresh native acceptance (2026-10-16 UTC)

Run `winreview1`, profile `coga-test`, us-east-1 / us-east-1a, t3.large:
instance `i-074adb93a0c32da8c`, AMI `ami-0b16ced290e00a1a3`,
`Windows_Server-2025-English-Full-Base-2026.10.14`. Launched 04:18:42Z.
Baseline: Server 2025 build 26100.33650, PowerShell 5.1.26100.33648,
Git 2.56.0.windows.2, uv 0.13.1, Administrator Python 3.11.17.

- Preflight and provision passed. Reused the previously owner-approved VPN
  source range; security group exposed SSH only.
- `checkout winreview1 main` cloned and `uv sync --extra test` passed;
  remote Python printed `win32`. Live argv checks preserved empty strings,
  shell operators, percent expansion syntax, apostrophes, double quotes,
  trailing backslashes, whitespace, newlines and Unicode. Stdin forwarding
  retained exit 37; explicit `cmd /c` with quoted ampersand retained exit 23.
  Receipts: local `remote-command-regressions.json` and `native-regressions.txt`.
- Drove `ssh winreview1` in a real 80x24 terminal: the cmd prompt was visible,
  `ver` printed the OS build, and `exit` closed the connection normally.
- PyPI `reviewwalk1` and main-wheel `reviewwalk3` passed every step through
  installation and first failed at `coga --version`, exit 1, missing `fcntl`.
  The wheel was coga-0.4.1 from fetched origin/main
  `87165c9c8471e204e267862c2034f40b578c0db7`. Both transcripts and step records
  were copied back. `reviewwalk2` stopped on the host's sandboxed uv cache
  before creating a Windows user; the authorized retry used a new walk name.
- `rdp winreview1` decrypted the admin password to local private storage;
  the printed tunnel on localhost:13390 returned an RDP X.224 Connection
  Confirm with NLA. **The owner still confirms a desktop session in the
  owner-held review step; that requires a fresh instance.**
- Teardown: instance terminated **04:29:10Z**, SG deleted **04:29:12Z**, key
  deleted **04:29:14Z**. Repeated teardown passed. `status` and AWS
  `describe-instances` confirmed terminated, with no tagged volumes;
  independent SG/key queries returned zero. Nothing from this run remains
  billing. All local evidence is under `.coga/clean-install/winreview1/`.

References for the findings: Microsoft's [cmd parser contract](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmd)
and [PowerShell error handling](https://learn.microsoft.com/en-us/PowerShell/module/microsoft.PowerShell.core/about/about_error_handling?view=powershell-5.1).

## PR

```yaml
title: Add the Windows EC2 clean-install harness
author: claude/codex
author_evidence: Claude Code authored the harness implementation; Codex independently reviewed it and
  authored the two review fixes. The final fixes received Codex self-review.
head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
depth: deep
rationale: Paid-cloud tooling with resource and credential lifecycle behavior. Direct review completed,
  both findings fixed, and fresh native acceptance passed. Read the dispatch tradeoff and self-review
  disclosure; the owner desktop RDP check remains for the review step.
implementation: aws-windows.sh drives AWS and SSH from the host (ledger, /32 or COGA_WIN_SSH_FROM SSH
  rule, RSA key, Server 2025 user data enabling sshd), windows-walk.ps1 runs baseline/setup/adduser/checkout/walk
  on the box under PowerShell 5.1; the windows-aws runbook and twin document cost, approval rule, provision,
  walk, fix loop, RDP and teardown. Review fixes preserve literal remote argv and command exit codes and
  correctly fail walk steps on non-terminating cmdlet errors.
deviations: Added COGA_WIN_SSH_FROM (owner-approved) because the owner's VPN exits from a range; walk
  users join OpenSSH Users because Windows' default sshd_config restricts logons to that group. Review
  fixes add iconv/base64 on the Unix host and encoded PowerShell dispatch; cmd /c explicitly requests
  shell parsing.
limitations: The owner has not yet confirmed a desktop RDP session; a fresh instance is needed in the
  owner review step. Codex independently reviewed the original Claude implementation but self-reviewed
  its own fixes. Linux suite used Python 3.12.12; native regression and walk checks used Python 3.11.17.
files:
  .gitattributes: Keep *.sh and *.ps1 LF so the scripts run from CRLF-prone checkouts.
  scripts/clean-install/aws-windows.sh: Host-side driver for the Windows harness.
  scripts/clean-install/windows-walk.ps1: Box-side baseline, setup, user creation, fix-loop checkout and
    walk.
  docs/contexts/coga/testing/clean-install/windows-aws/SKILL.md: New runbook topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/clean-install/windows-aws/SKILL.md: Packaged
    twin of the runbook.
  docs/contexts/coga/testing/clean-install/SKILL.md: Link the Windows harness from the parent topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/clean-install/SKILL.md: Twin of the
    parent-topic link.
  docs/contexts/coga/testing/SKILL.md: Link the Windows harness from coga/testing.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/SKILL.md: Twin of the coga/testing
    link.
  docs/README.md: Index the new runbook.
  tests/test_packaging.py: Require the windows-aws bootstrap context ref.
  tests/test_windows_clean_install.py: Host transport/exit-code/encoding regression plus native PowerShell
    first-failure and stderr regression cases.
review:
  reviewer: codex
  kind: self
  status: passed
  head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
  base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
  detail: Direct review completed on the final diff with no unresolved must-fix findings. Codex independently
    reviewed Claude implementation, then authored and self-reviewed two owner-approved fixes. Native regressions,
    remote commands, real 80x24 SSH terminal, fresh-user walks and RDP protocol tunnel were exercised;
    desktop confirmation belongs to the owner review step.
checks:
- command: .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: 47aa80b1619aa500de664e14084eed70fa9d1f2d
  base: da4b0436266a5ce1039c4017765b0fd75bd03b5c
  detail: 3669 passed.
- command: AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh preflight/provision/checkout/ssh/walk/rdp/teardown/status
    (run win3)
  status: passed
  head: 47aa80b1619aa500de664e14084eed70fa9d1f2d
  base: da4b0436266a5ce1039c4017765b0fd75bd03b5c
  detail: Live run on uncommitted script versions whose content equals the commit's for the box script;
    driver gained keepalives and the trailing-slash fix during the run (both exercised after the change).
    win32 printed; walks failed at coga --version (fcntl) as expected; teardown left nothing billing.
- command: PYTHONPATH="$PWD/src" .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  detail: 3673 passed, 5 skipped in 360.58s on Python 3.12.12. The five skipped PowerShell cases were
    run natively below.
  head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
  base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
- command: AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh ssh winreview1 uv run --with pytest
    --python 3.11 python -m pytest -q -p no:cacheprovider C:/coga-clean-install/coga-windows-native-review/tests/test_windows_clean_install.py
    -k test_windows_walk_records_first_failure
  status: passed
  detail: 5 passed, 1 deselected in 29.19s on native Windows Python 3.11.17 / PowerShell 5.1.26100.33648.
    Covers non-terminating Get-Item/Get-FileHash errors, a missing command, and native stderr with exits
    0 and 23.
  head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
  base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
- command: 'AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh preflight us-east-1

    AWS_PROFILE=coga-test COGA_CLEAN_INSTALL_ALLOCATE=yes COGA_WIN_SSH_FROM=149.36.48.0/24 scripts/clean-install/aws-windows.sh
    provision winreview1 us-east-1 us-east-1a

    AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh checkout winreview1 main

    AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh ssh winreview1 python -c "import sys; print(sys.platform)"

    AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh walk winreview1 pypi reviewwalk1 installer

    AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh walk winreview1 main reviewwalk3 installer'
  status: passed
  detail: 'Fresh run: i-074adb93a0c32da8c, ami-0b16ced290e00a1a3 (Windows_Server-2025-English-Full-Base-2026.10.14),
    us-east-1/us-east-1a, t3.large. Provision and checkout passed; win32 printed. Both walks first failed
    at coga --version with exit 1 / missing fcntl, as expected. Main wheel coga-0.4.1 came from fetched
    origin/main 87165c9c8471e204e267862c2034f40b578c0db7. Host uv cache needed sandbox escalation; aborted
    reviewwalk2 never created a Windows user.'
  head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
  base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
- command: AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh ssh winreview1
  status: passed
  detail: Real 80x24 PTY displayed cmd prompt; ver printed build 10.0.26100.33650 and exit closed normally.
    Separate subprocess probes recorded in remote-command-regressions.json passed literal argv round-trip,
    stdin with exit 37, and explicit cmd /c with quoted ampersand and exit 23.
  head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
  base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
- command: AWS_PROFILE=coga-test COGA_WIN_RDP_PORT=13390 scripts/clean-install/aws-windows.sh rdp winreview1
  status: passed
  detail: Admin password retrieved into private local storage. Printed SSH tunnel returned RDP X.224 Connection
    Confirm with NLA on localhost:13390; tunnel was closed after the probe. Desktop login is not claimed.
  head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
  base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
- command: 'AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh teardown winreview1

    AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh teardown winreview1

    AWS_PROFILE=coga-test scripts/clean-install/aws-windows.sh status winreview1

    aws --profile coga-test --region us-east-1 ec2 describe-instances --instance-ids i-074adb93a0c32da8c
    --query ''Reservations[].Instances[].[InstanceId,State.Name]'' --output text'
  status: passed
  detail: Terminated 2026-10-16T04:29:10Z; SG deleted 04:29:12Z; key deleted 04:29:14Z. Repeat teardown
    passed. status and describe-instances confirmed terminated, no tagged volumes; separate security-group
    and key-pair queries returned zero. Nothing from this run remains billing.
  head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
  base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
- command: 'bash -n scripts/clean-install/aws-windows.sh

    git diff --check origin/main...HEAD

    git ls-files --eol scripts/clean-install/aws-windows.sh scripts/clean-install/windows-walk.ps1'
  status: passed
  detail: Shell syntax and whitespace passed. Both scripts are LF in the index. All three changed canonical/packaged
    context pairs are byte-identical after rebase; packaging tests passed in the full suite.
  head: a12cf28fde18ef4f4f430e3bd56065725550f6e7
  base: 6f2316b71821fb181a3aa49f47339b91e0ad33f6
- command: Owner desktop RDP login
  status: not-run
  detail: Explicitly deferred by the ticket to the owner-held review step. Fresh provision required; the
    review instance was torn down.
```
