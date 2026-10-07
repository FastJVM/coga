---
name: coga/testing/clean-install/macos-owned
description: The default macOS clean-install path on owner-provided Macs over SSH — a disposable Tart VM on Apple silicon for fresh installs, an attached Intel Mac for compatibility, the disposable-only reset rule, cleanup, and cost choice versus EC2 Mac and hosted CI.
---

# macOS clean-install harness on owned Macs

This is the default way to run the macOS walk. It runs the same
`scripts/clean-install/container.sh` walk as the
[EC2 Mac harness](../macos-aws/SKILL.md), as a fresh macOS user, but on Macs the
owner already has. The walk itself is the same: PyPI or a `main` wheel, then
`coga init` and `coga validate`, with the same evidence. The driver also
reuses the EC2 harness's Mac-side `macos-walk.sh`. EC2 Mac stays an option
for when no owned Mac is available.

- `scripts/clean-install/owned-mac.sh` runs on your machine and reaches the
  Mac over SSH.
- `scripts/clean-install/mac-common.sh` holds the walk, evidence and VNC
  steps that both drivers share.

## Which Mac proves what

| Target | Command | What it proves |
|---|---|---|
| Apple silicon Mac | `vm` | **A fresh install.** Each run clones a new macOS VM with no Command Line Tools (CLT), walks it, and deletes it. |
| Intel Mac (or any Mac used as-is) | `attach` | **Compatibility only**, for example the x86_64 wheel, uv and Python. |

A fresh user account isolates only its home. CLT, Xcode, Homebrew (on Intel
`/usr/local/bin`, which is on every user's `PATH`), `/etc/paths`, and anything
else machine-wide stay as the Mac has them. `baseline.txt` records that state,
so read it before reporting an attached walk.

macOS VMs (Apple's Virtualization framework, which Tart uses) need Apple
silicon. A fresh Intel install would need a VM product that supports macOS
guests on Intel, such as VMware Fusion; the driver does not automate that. If
you build such a VM by hand, attach it like any other Mac. Then, inside it
and only there, you may run `bash /tmp/coga-clean-install/macos-walk.sh
designate-disposable <name>` followed by `reset`. macOS 26 is the last
release for Intel Macs.

## Reset is for disposable Macs only

Two Mac-side steps are destructive. `reset` deletes
`/Library/Developer/CommandLineTools`, and `vnc` replaces the admin user's
password. Both refuse to run unless `/etc/coga-disposable-test-mac` exists.
Only `designate-disposable` writes that file, and the drivers call it only on
machines they created and will destroy: `owned-mac.sh vm` on its cloned VM,
and `aws-mac.sh provision` on its EC2 instance. `attach` never designates a
Mac, never resets it, and has no `vnc`. Never run `designate-disposable` on an
ordinary Mac.

## One-time setup

**Apple silicon Mac** (the VM host):

1. Turn on **Remote Login**, and allow key-based SSH from the operator's
   machine for one account. That account's login shell must find `tart`.
2. Install Tart: `brew install cirruslabs/cli/tart`. It is free for personal
   use and for organizations up to 100 host CPU cores
   ([licensing](https://tart.run/licensing/)).
3. Keep that account logged in at the Mac. If `tart run` fails over SSH
   without a GUI session, start the VM from the Mac's Terminal instead.
4. Leave room for the image: the first `vm` pulls the whole vanilla image
   into Tart's cache, and later clones are copy-on-write. Apple's licence
   allows at most two macOS VMs per Mac at once.

**Intel Mac**: turn on **Remote Login** and create a dedicated admin test
account, not the owner's own account. Give it passwordless sudo, which the
walk needs to create users, with a drop-in such as
`/etc/sudoers.d/coga-test` containing `<account> ALL=(ALL) NOPASSWD: ALL`.
Remove that file when testing ends. `attach` checks `sudo -n true` before it
copies anything.

Check either Mac read-only first:

```sh
./scripts/clean-install/owned-mac.sh preflight tester@mac-mini.local
```

This prints the macOS version, architecture, CPUs, memory, free disk, Tart's
version and VMs, and whether sudo needs a password.

## Fresh install on the Apple silicon VM

```sh
./scripts/clean-install/owned-mac.sh vm m1 tester@mac-mini.local
./scripts/clean-install/owned-mac.sh walk m1 pypi walk1 installer
```

`vm` runs these steps:

1. Refuses a non-arm64 host.
2. Clones the image (default `ghcr.io/cirruslabs/macos-tahoe-vanilla:latest`;
   pass an `IMAGE` argument or set `COGA_MAC_VM_IMAGE` to pin one) into
   `coga-clean-install-<name>`.
3. Starts the VM headless and waits for its IP on the Mac's private network.
4. Uses the image's default `admin`/`admin` login once, through
   `SSH_ASKPASS`, to install this run's new SSH key. Every later call uses
   that key through `ProxyJump` via the Mac. `COGA_MAC_VM_USER` and
   `COGA_MAC_VM_PASSWORD` override the login.
5. Copies the walk scripts, records `baseline.txt`, designates the VM
   disposable, and runs `reset`. On a vanilla image `reset` only verifies
   that a new user's `git` resolves to the `/usr/bin` shim.

Walks, CLT installation, and the attended agent login and first ticket then
follow the [EC2 runbook](../macos-aws/SKILL.md#walk) with `owned-mac.sh` in
place of `aws-mac.sh`. The Python 3.11 caveat there applies here too.

```sh
./scripts/clean-install/owned-mac.sh walk m1 main walk2 installer
./scripts/clean-install/owned-mac.sh ssh m1 sudo -iu walk2
./scripts/clean-install/owned-mac.sh vnc m1     # GUI, e.g. the CLT dialog
```

The first walk stops at `git --version` because the VM has no CLT. That is
the new-user finding. Install the CLT over VNC or headless, then walk again
with a **new** user. To see the missing-CLT experience again, clean up and
create a new VM rather than resetting this one.

## Compatibility walk on the Intel Mac

```sh
./scripts/clean-install/owned-mac.sh attach i1 cogatest@imac.local
./scripts/clean-install/owned-mac.sh walk i1 pypi walk1 installer
./scripts/clean-install/owned-mac.sh walk i1 main walk2 installer
```

Each walk still creates its own macOS user and installs uv, Coga and the
agent in that user's home. Use the Mac's own Screen Sharing, not `vnc`, for
GUI steps.

## Evidence and cleanup

Evidence uses the EC2 layout under `.coga/clean-install/<name>/` (gitignored):
`resources.env` (`KIND`, `HOST`, and for a VM `IMAGE`, `TART_VERSION`, `VM`,
`VM_IP`), `host.txt`, `baseline.txt`, and for each walk `walks/<user>/` with
`result.txt`, `password.txt`, `source.txt` and the wheel for `main`, and
`mac/evidence/` (transcript, steps, init result). Report each walk's artifact,
version and commit, its first failing step or init pass, whether the attended
first ticket ran, and, for an attached Mac, its baseline.

```sh
./scripts/clean-install/owned-mac.sh cleanup m1
./scripts/clean-install/owned-mac.sh cleanup i1
```

For a VM, `cleanup` stops and deletes it, and with it everything the walks
installed. For an attached Mac, it deletes only the walk users recorded under
`walks/`, with their homes, and the copied scripts. It leaves alone any CLT
you installed there and anything else machine-wide. Each step is recorded in
`resources.env`, so rerunning `cleanup` is safe. Tart's image cache stays on the
Mac for the next clone; `tart prune` reclaims it.

## Cost and choosing a path

Owned Macs cost nothing per run. An EC2 Mac host bills at least 24 hours (at
least USD 15.60 for `mac2` in us-east-1) and needs spend approval each time.
Hosted per-minute runners preinstall Xcode, so they cannot show the
missing-CLT first run, and GitHub's have no interactive login. They fit only
an automated install/init/validate smoke check. Adding one would change the
[no-CI posture](../../SKILL.md#ci-posture-and-receipts) and needs an explicit
owner decision. The dated rates, the per-path comparison and the
recommendation are in the dated
`docs/evidence/macos-install-test-costs.md`.
