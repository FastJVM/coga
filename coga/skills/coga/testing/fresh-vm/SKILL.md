---
name: fresh-vm
description: Prepare, verify, and reuse a spare `cogatest` VM (UTM macOS guest or VirtualBox Windows 11) for an attended human test, so the machine state is a fact rather than an assumption. Shared by the attended install walk and hands-on competitor trials.
---

# Fresh `cogatest` VM

An attended test, where a human installs something by hand while an agent
session on their normal account records what happens, is only as good as the
machine it starts on. This skill owns how that machine is made, checked, and
reused. What the human does on it belongs to the calling skill: the
[attended install walk](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/human-walk/SKILL.md)
for Coga's own install, or a competitor trial.

The plain-language steps for a non-engineer to build the VM are in the walk's
[operator guide](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/human-walk/operator-guide.md),
Part 1. This page holds the agent-side facts behind them.

## VM first, new account only for a re-walk

Use a VM. A new user account on the human's own machine is instant and free,
but it inherits every machine-wide install, so the steps a fresh machine
fails on look easy:

- **macOS:** the Command Line Tools (so `git` works and its install popup never
  appears), Homebrew under `/opt/homebrew`, and python.org Python in
  `/usr/local/bin` (so the Python 3.11 floor looks met).
- **Windows:** Git for Windows, an "all users" Python, and machine-wide winget
  packages.

A new account is acceptable for re-walking one step after a fix. Flag every
finding that depends on those leaked tools as "machine-wide, not a real test",
never as "worked".

## macOS guest (UTM, Apple silicon)

- **Free space: about 45 GB.** UTM downloads a ~15 GB restore image and the
  guest grows to ~25 GB once installed, regardless of the 64 GB virtual disk.
- **UTM cannot snapshot a macOS guest.** The spare is a **Clone**, taken right
  after the baseline (below) with the VM shut down.
- **Delete the cached restore image before cloning:**
  `rm ~/Library/Containers/com.utmapp.UTM/Data/Library/Caches/*.ipsw`
  (about 18 GB; UTM refetches it when needed). Cloning first can fill the
  host disk partway through the walk, which looks like a failure of the thing
  under test. The clone itself is nearly free (APFS shares the blocks) and
  grows only as the working copy diverges.
- Run the original and keep the clone sealed as the next bare spare.
- **No shared clipboard.** UTM shares no clipboard with a macOS guest. The human
  copies from the guest's own browser into the guest's terminal, which is what
  a real user does. Anything the agent wants run goes into a published
  artifact the human opens in the guest browser (`claude.ai/code/artifacts`
  lists them by title, so no URL is typed), never only into chat. A typo in a
  command the human had to retype out-of-band is a VM artifact, not a finding.

## Windows 11 guest (VirtualBox)

- Tick **Skip Unattended Installation** when creating the VM. Without it
  VirtualBox bypasses the setup screens (OOBE) and creates a `vboxuser`
  account, so first-run experience is never seen.
- No product key: **I don't have a product key**, Windows 11 Home.
- Local account without Microsoft sign-in: at the network screen press
  Shift+F10 and run `start ms-cxh:localonly`. If that fails and a throwaway
  Microsoft account is used, record it.
- Take a VirtualBox snapshot right after the baseline; restoring it is the
  spare.
- Slowness on a host that also runs WSL or Hyper-V is the host, not a finding.

## Baseline

Record the bare state before installing anything, and have the human paste
it into the agent session. The macOS command must not invoke the `git` or
`python3` stubs: on a fresh Mac `/usr/bin/git` and `/usr/bin/python3` are
Command Line Tools stubs that open an install popup, and Python 3.9 appears
only after that install. `which -a` names them without running them.

```sh
sw_vers; uname -m; xcode-select -p; which -a git python3 brew uv coga claude gh
```

On a bare Mac `xcode-select -p` errors and only the two `/usr/bin` stubs are
found. Add the tool under test's own command names to the `which -a` list.

```powershell
[Environment]::OSVersion; Get-ExecutionPolicy; Get-Command git,python,py,uv,coga,claude,gh,winget -ErrorAction SilentlyContinue | Format-Table Name,Source
```

## Reusing a spare

At the start of every session, have the human confirm **which** machine and
that it was **reverted to bare**: a fresh clone of the sealed macOS spare, or
the restored Windows snapshot. Then rerun the baseline and compare. Do not
take "it's clean" on trust: a 2026-10-24 competitor trial left an agent CLI,
a Python venv, and its scratch project on a `cogatest` VM, and installing on
that machine would have voided the prerequisite comparison with every other
run.

Steps the human performs from habit (installing the Command Line Tools before
anything asked for them, say) are not demands of the thing under test. Ask
when unsure, and record them as the operator's steps.

## Teardown

Delete a used working copy (UTM or VirtualBox: right-click, Delete) and keep
the sealed spare. Remove a new `cogatest` user account once its re-walk is
recorded.
