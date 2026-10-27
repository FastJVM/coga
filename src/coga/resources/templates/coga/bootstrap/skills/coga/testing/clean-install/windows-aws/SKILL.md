---
name: windows-aws
description: Provision, use, and tear down an AWS Windows host for Coga clean-install verification or the native Windows fix loop, including attended SSH or RDP checks.
---

# Windows clean-install harness on AWS

The Windows counterpart of the [macOS harness](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/macos-aws/SKILL.md). It rents
a fresh native Windows machine (EC2 Windows Server 2025), drives it over SSH,
and throws it away. It serves two purposes. **Walks** run the documented
[install](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/install/SKILL.md) and [init](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/init/SKILL.md) path as
a new local user. The **fix loop** checks out a branch and runs commands and
the test suite on native Windows for the `windows-native/` port. Like the other
harnesses, it is repository tooling and is not installed with Coga:

- `scripts/clean-install/aws-windows.sh` runs on your machine. It drives the
  AWS CLI, SSH, and the build of a fetched-ref wheel.
- `scripts/clean-install/windows-walk.ps1` runs on the instance under the stock
  Windows PowerShell 5.1. Provision copies it to `C:\coga-clean-install\`.

Server 2025 is not a Windows 11 desktop: it has no Store or winget-first
setup, and its Git for Windows comes from the harness. The owner accepted
these gaps for automated evidence. A human Windows 11 walk is separate work.

## Cost and approval

Windows EC2 bills per second while the instance exists: compute with the
Windows licence, plus the EBS disk until termination. There is no dedicated
host and no minimum term. The default `t3.large` with a 50 GB gp3 disk costs
about USD 0.11 per hour in us-east-1. `COGA_WIN_INSTANCE_TYPE` and
`COGA_WIN_DISK_GB` override the size.

`provision` refuses unless `COGA_CLEAN_INSTALL_ALLOCATE=yes` is set.
**Approval rule (owner decision 2026-10-14):** the owner approves the first
provision. After that, agents working `windows-native/` tickets may provision
and tear down Windows instances without asking again, **provided every session
ends with `teardown`** and `status` confirms it. Any other use, a larger
instance type, or an instance left running between sessions needs the owner's
approval.

## Credentials and region

Use an AWS SSO profile, never root credentials. The repository is public:
never write account IDs, emails, keys or passwords into tickets, logs or PRs.

```sh
aws sso login --profile <profile>   # add --use-device-code --no-browser when headless
export AWS_PROFILE=<profile>        # aws-windows.sh passes it on every aws call
./scripts/clean-install/aws-windows.sh preflight us-east-1
```

`preflight` is read-only. It prints the caller, the on-demand standard vCPU
quota, the zones offering the instance type, any harness instances not yet
terminated, and the newest `Windows_Server-2025-English-Full-Base-*` AMI.

The host needs Bash, the AWS CLI v2, OpenSSH 8.4 or newer (walk logons use
`SSH_ASKPASS_REQUIRE`), `ssh-keygen`, `openssl`, `curl`, `iconv`, `base64`, and uv for fetched-ref
walks.

## Provision

```sh
COGA_CLEAN_INSTALL_ALLOCATE=yes \
  ./scripts/clean-install/aws-windows.sh provision win1 us-east-1
```

An optional third argument picks the zone; without one, the first zone with a
default subnet that offers the instance type is used. `provision`:

- creates an **RSA** key pair (`get-password-data` decrypts the Administrator
  password only with RSA) and a security group allowing SSH only from your
  current public IP (`/32`). Port 3389 is never opened. Behind a VPN that
  leaves from several addresses (SSH then works only intermittently), set
  `COGA_WIN_SSH_FROM` to the exit range, for example `198.51.100.0/24`.
  Anyone on that range can then reach `sshd`, which accepts only the key
  and the walk users' random passwords.
- launches the newest Server 2025 AMI (`COGA_WIN_AMI=ami-…` pins one) with
  IMDSv2 required. Its first-boot user data (`<powershell>`) adds the OpenSSH
  Server capability if missing, installs the harness public key in
  `administrators_authorized_keys`, starts `sshd`, and opens 22 in the Windows
  firewall. The user data is saved as `user-data.ps1`.
- waits for SSH as `Administrator` (up to 20 minutes; first boot usually takes
  5–15), copies `windows-walk.ps1`, and writes `baseline.txt`: the OS build,
  PowerShell, git, Python, uv and `sshd`, as launched and after setup.
- **setup** installs the latest Git for Windows machine-wide with installer
  defaults (including `core.autocrlf=true`, as a real user gets). It then
  installs uv with its official installer and runs
  `uv python install 3.11 --default` **for Administrator only**.

Each resource ID is appended to `.coga/clean-install/<name>/resources.env`
(gitignored) as soon as it exists, so a failed provision can still be torn
down. Driver output goes to `host.txt`.

## Walk

```sh
./scripts/clean-install/aws-windows.sh walk win1 pypi walk1 installer
./scripts/clean-install/aws-windows.sh walk win1 main walk2 installer
./scripts/clean-install/aws-windows.sh walk win1 my-branch walk3 installer
```

Each walk creates a **new local user** (`walk1`), in Users, Remote Desktop
Users and OpenSSH Users, with a random password saved in `walks/<user>/password.txt`. The
password goes over stdin, never onto a command line. The driver then opens a
password SSH logon as that user, so the walk runs with its own fresh profile.
Windows' default `sshd_config` ends with
`AllowGroups administrators "openssh users"`; without OpenSSH Users, sshd
logs "none of user's groups are listed in AllowGroups" and refuses the
logon even with the right password.
`uv tool install` is per user, so nothing from the Administrator fix loop
leaks into a walk. As that user, `windows-walk.ps1 walk` runs the same steps
as `container.sh`:

1. `whoami`, then `git --version`;
2. uv's official installer (`irm https://astral.sh/uv/install.ps1 | iex`),
   `uv --version`, `uv python install 3.11`, and **only then**
   `UV_PYTHON=3.11` and `UV_PYTHON_DOWNLOADS=never`, followed by
   `uv python find 3.11` and a 3.11 version check. `never` set earlier would
   block the install; the macOS walk uses the same order;
3. `uv tool install --python 3.11 coga` (from PyPI or the wheel);
4. `coga --version`, then `uv tool list`;
5. `git init -b main`, a local test identity, then
   `coga init --user <operator>`;
6. `coga validate --json`.

Any artifact argument other than `pypi` names a ref to fetch from `origin`
(a branch, tag, or full commit ID). `main` remains the ordinary main-wheel
spelling. The driver builds from that exact fetched commit, never from the
working tree, and copies only that wheel to the instance. For a port fix loop,
push the branch first, then walk that branch as a new local user; a successful
Administrator checkout is separate evidence from this fresh-user install.

Evidence for each walk is in `.coga/clean-install/<name>/walks/<user>/`:
`result.txt` (exit code), the wheel and `source.txt` for fetched refs, and
`windows/evidence/`, which holds `transcript.txt`, `steps.txt` (`PASS` lines
and the first `FAIL (exit N)`), and `init-passed.txt` when init succeeds.
Native commands retain their exit code; cmdlet errors fail with code 1,
including non-terminating errors. Native stderr alone is not a failure.
The core port verifies this entire walk. Agent-session checks are separate:
until `v1/14-interactive-coga-launch-on-native-windows` lands,
those commands refuse before starting an agent.

To continue as the walk user, the driver prints an
`ssh <user>@<ip>` command that takes the password from `password.txt`.

## Fix loop: checkout and remote commands

```sh
./scripts/clean-install/aws-windows.sh checkout win1 my-branch    # or a full SHA
./scripts/clean-install/aws-windows.sh ssh win1 python -c "import sys; print(sys.platform)"
./scripts/clean-install/aws-windows.sh ssh win1 uv run --directory coga-work python -m pytest -x
```

`checkout` runs as Administrator in `%USERPROFILE%\coga-work`. It clones the
public repository over HTTPS (derived from `origin`; `COGA_WIN_REPO_URL`
overrides it) on first use. It fetches the ref, detaches at it, and runs
`uv sync --extra test`. It refuses when the box checkout has uncommitted
changes: push fixes from the host and check out again, rather than editing on
the box.

`ssh NAME CMD…` runs one executable as Administrator from its home directory
and **exits with its exit code**. An encoded PowerShell wrapper starts the
process directly, preserving empty arguments, embedded quotes, and literal
shell characters such as `&` and `%`. For shell builtins or a compound line,
pass the line to `cmd /c` as one word (that explicitly requests shell parsing).
`ssh NAME` alone opens an interactive `cmd` prompt.

### Long native runs

The full native `python -m pytest` takes about two hours, longer than an SSH
session or agent tool server reliably lives (transport exit 255). Run it as a
temporary Administrator S4U scheduled task that writes stdout, stderr, JUnit
XML and the exit code under `C:\coga-clean-install\`, and poll with brief
reconnects. Stopping the task's PowerShell action leaves its `uv` child
running: stop the owned process tree, verify no Python, Git or uv process
remains, and delete the task before teardown. If SSH fails with exit 255
while instance checks stay healthy, your public IP probably changed: replace
the security group's single-host `/32` with the new `/32` rather than widening it.
Windows Defender can dominate Git cost; temporary exclusions (checkout,
pytest temp, `C:\Program Files\Git`) need owner approval and must be removed
and verified before teardown. An expired SSO session blocks `teardown`, so
refresh it before the session ends.

## RDP

```sh
./scripts/clean-install/aws-windows.sh rdp win1
```

`rdp` fetches and decrypts the Administrator password with
`ec2 get-password-data` and the key pair (EC2Launch publishes it a few
minutes after first boot; retry if it is not ready). It saves the password in
`admin-password.txt`, never on screen, and prints an SSH tunnel command:
`ssh … -N -L 13389:localhost:3389 Administrator@<ip>` (`COGA_WIN_RDP_PORT`
changes the local port). With the tunnel open, connect an RDP client to
`localhost:13389`, for example Microsoft Remote Desktop, `xfreerdp` or
Remmina, as Administrator or as a walk user with its `password.txt`. Use RDP
for the attended `coga launch` check, which needs a real console.

Known gap (unverified, no follow-up ticket): the harness's acceptance required
the owner to confirm that an RDP desktop session opens, and that check was
never run. The review instance was torn down first, so confirming it needs a
fresh provision. The `rdp` password retrieval and its SSH tunnel were checked
(the tunnel answered with an RDP Connection Confirm), but no desktop login was.
Until someone logs in to a desktop through that tunnel, treat the RDP desktop
path, and so the attended `coga launch` check above, as unverified.

## Teardown

```sh
./scripts/clean-install/aws-windows.sh teardown win1
./scripts/clean-install/aws-windows.sh status win1
```

`teardown` terminates the instance and waits for termination. The root volume
is deleted with it. Then it deletes the security group and the key pair. Each
step is recorded in `resources.env`, so rerunning `teardown` is safe.
`status` shows the instance state, any volume still tagged for the run, and
any security group or key pair not yet deleted. A finished run shows
`terminated` and nothing else. Every session that provisions must end here.

For a PR, report the instance ID, the AMI and its name, the region and zone,
each walk's artifact and first failing step (or init pass), and the teardown
time. Recording a failure is evidence, not a fix.
