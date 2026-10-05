---
name: coga/testing/clean-install/macos-aws
description: The macOS clean-install harness on an EC2 Mac dedicated host — cost approval, region choice, provision, install/init walk, SSH or VNC continuation, and teardown with host release.
---

# macOS clean-install harness on AWS

The macOS counterpart of the [Linux clean-install harness](../SKILL.md). It
runs the same walk script, `scripts/clean-install/container.sh`, as a fresh
macOS user on an EC2 Mac (`mac2.metal`, Apple silicon), and checks the
documented [install](../../../install/SKILL.md), [init](../../../init/SKILL.md)
and [first-task](../../../first-task/SKILL.md) path against an installed
artifact. Like the Linux harness, it is repository tooling and is not
installed with Coga:

- `scripts/clean-install/aws-mac.sh` runs on your machine. It drives the AWS
  CLI, SSH and the build of the `main` wheel.
- `scripts/clean-install/macos-walk.sh` runs on the Mac as `ec2-user`.

## Cost and approval

An EC2 Mac runs only on a **dedicated host**. The host bills for at least 24
hours from allocation and **cannot be released sooner**, even after its
instance terminates. Allocating one spends money, so get the owner's approval
of the region and the cost first. `provision` refuses to run unless you set
`COGA_CLEAN_INSTALL_ALLOCATE=yes`. Plan to run every walk you need on one host
within its first day.

**Reusing an already-allocated host takes a manual step.** `provision` always
calls `ec2 allocate-hosts` and has no option to target an existing host, so a
later provision name cannot reuse a host that an earlier one allocated (for
example one still inside its 24-hour minimum). The 2026-10-01 run reused
`h-0833c01ac15e645ac` this way. The owner approved the reuse separately from
the original allocation. The operator ran a temporary, untracked copy of
`aws-mac.sh` that substituted the existing host ID for the allocation call,
and left the tracked harness unchanged. The new provision's `resources.env`
then owns that host. Its standard `teardown <name>` released it, so that
ledger, not the original one, must record `HOST_RELEASED`.

## Credentials and region

Use an AWS SSO profile, never root credentials:

```sh
aws sso login --profile <profile>
export AWS_PROFILE=<profile>      # aws-mac.sh passes it on every aws call
./scripts/clean-install/aws-mac.sh preflight us-east-1
```

`preflight` is read-only. It prints the caller, the account's `mac2` dedicated-host
quotas, the availability zones that offer `mac2.metal`, any existing `mac2`
hosts, and the newest arm64 macOS AMI. `mac2` capacity varies by region and
zone, and a new account's quota can be 0. Pick a region close to the
operator with a quota of at least 1 (request an increase in Service Quotas if
needed), and choose one of the listed zones. Allocation can still fail with
`InsufficientHostCapacity`; if it does, try another listed zone.

## Provision

```sh
COGA_CLEAN_INSTALL_ALLOCATE=yes \
  ./scripts/clean-install/aws-mac.sh provision mac1 us-east-1 us-east-1a
```

This command:

- creates an ed25519 key pair and a security group that allows SSH only from
  your current public IP (`/32`);
- allocates a host and launches the newest `amzn-ec2-macos-*` arm64 AMI on
  it, in the zone's default subnet. Set `COGA_MAC_AMI=ami-…` to pin an AMI.

Each resource ID is appended to `.coga/clean-install/<name>/resources.env`
(gitignored) as soon as the resource exists, so a failed provision can still be
torn down. A failed AWS resource-creation call stops provisioning without
recording an empty ID or attempting later allocations. The SSH wait allows
30 minutes, because an EC2 Mac can take 10–20 minutes to become reachable.

Then `provision` copies both scripts to `/tmp/coga-clean-install/` and saves a
`baseline.txt`: the macOS version, the Command Line Tools (CLT) state, Homebrew
and `/etc/paths`. After that it **removes the CLT that the AMI ships**, using
Apple's uninstall (delete `/Library/Developer/CommandLineTools`). It checks that
a fresh login shell resolves `git` to the `/usr/bin` shim. It never preinstalls
CLT. A new Mac user meets the CLT prompt at their first `git` call, and so does
the harness. The AMI's CLT receipts stay: they live under SIP in
`/Library/Apple/System/Library/Receipts`, which `pkgutil --forget` does not
touch. On the 2026-09-30 run they did not stop `softwareupdate` from offering
the CLT again.

## Walk

```sh
./scripts/clean-install/aws-mac.sh walk mac1 pypi walk1 installer
./scripts/clean-install/aws-mac.sh walk mac1 main walk2 installer
```

Each walk creates a new macOS user (`walk1`) with a fresh home and a random
password, saved in `walks/<user>/password.txt`. In a login shell as that user,
it installs uv with its official installer and then runs `container.sh`. The
steps match the Linux container:

1. `id`, then `git --version`;
2. `python3 --version` and `uv --version`;
3. `uv tool install coga` (from PyPI or the wheel);
4. `coga --version` and `uv tool list`;
5. `git init`, then `coga init --user <operator>`;
6. `coga validate --json`.

`main` mode builds the wheel on your machine from the fetched `origin/main`,
not from your working tree, and copies only that wheel to the Mac.

**The walk does not pin Python 3.11.** Step 2 only reports `python3`. After
the CLT install, the Mac's default `/usr/bin/python3` is 3.9.6, which is
below Coga's 3.11 floor. A result produced there is not evidence about a
supported interpreter. On 2026-10-01 an earlier walk that resolved the PyPI
`0.0.1` placeholder was set aside for this reason. Install and select 3.11 explicitly for the walk user,
and record the interpreter in the evidence. The draft
`marketing/fix-installer/pin-python-3-11-in-the-macos-clean-install-harness`
owns the harness fix. It is unresolved on `main`: `container.sh` still runs a
bare `python3 --version`.

**Expect the first walk to stop at `git --version`.** The shim exits non-zero.
Over SSH no GUI session owns the walk user, so it prints `xcode-select: error:
No developer tools were found and no install could be requested (possibly
because there is no active GUI session)`; a user at the Mac's screen gets the
install dialog instead. That stop is the new-user finding. To continue, install
the CLT: as a new user would, over VNC (below) by clicking **Install** in the
dialog or accepting `xcode-select --install`; or headless over SSH:

```sh
touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
softwareupdate -l          # note the "Command Line Tools for Xcode" label
sudo softwareupdate -i "<that label>"
rm /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
```

Then run a walk with a **new** macOS user. The CLT install is machine-wide;
homes are not shared.

Evidence for each walk is in `.coga/clean-install/<name>/walks/<user>/`:
`result.txt`, the wheel and `source.txt` for `main`, and `mac/evidence/`, which
holds `transcript.txt`, `steps.txt` (first failure and its exit code) and
`init-passed.txt`. Driver output goes to `host.txt`. New evidence is
owner-readable only; generated passwords are omitted from command traces and remain in their
separate password files. Host wheel checksums use `sha256sum` or macOS
`shasum -a 256`.

## Attended continuation: SSH or VNC

**SSH is enough for the agent login and the first ticket.** Log in as the walk
user:

```sh
./scripts/clean-install/aws-mac.sh ssh mac1 sudo -iu walk2
```

Then, as that user, follow the vendor's
[Claude Code setup](https://code.claude.com/docs/en/setup):

```sh
curl -fsSL https://claude.ai/install.sh | bash
claude        # finish browser login with the URL it prints, then exit
bash /tmp/coga-clean-install/macos-walk.sh ticket "Write a hello-world script" --agent claude
```

Check `~/clean-install/repo/coga/tasks/` to confirm the ticket was written.

**Use VNC for GUI flows** (the CLT dialog, a browser on the Mac):

```sh
./scripts/clean-install/aws-mac.sh vnc mac1
```

This command sets a random password for `ec2-user` (saved in
`vnc-password.txt`) and enables Screen Sharing. It then prints an SSH tunnel
command: `ssh -N -L 5900:localhost:5900 …`. With the tunnel open, connect a VNC
client to `vnc://localhost:5900`: macOS Screen Sharing, or TigerVNC or Remmina
on Linux. Port 5900 is never opened in the security group. At the login
window, either user works: `ec2-user`, or a walk user with its
`password.txt`.

## Teardown and host release

```sh
./scripts/clean-install/aws-mac.sh teardown mac1
./scripts/clean-install/aws-mac.sh status mac1
```

`teardown` terminates the instance and waits for termination. It then deletes
the security group and the key pair, and tries to release the host. Each step is
recorded in `resources.env`, so rerunning `teardown` is safe.

Inside the first 24 hours, AWS refuses the release. `teardown` prints `NOT
released` with AWS's message and exits 1. After termination, the host also sits
in `pending` while AWS scrubs it. Once 24 hours have passed from
`HOST_ALLOCATED_AT` and the host is `available`, run:

```sh
./scripts/clean-install/aws-mac.sh release mac1
```

A host that is never released **keeps billing**. It is not torn down until
`resources.env` records `HOST_RELEASED`. Also confirm that the console or
`aws ec2 describe-hosts` shows it `released`.

For a PR, report the resource IDs (host, instance, AMI and its name, region
and zone), each walk's artifact, version and first failing step (or init pass),
the teardown and release times, and whether the attended first ticket ran.
Recording a failure is evidence, not a fix; issue filing belongs to its own
ticket.
