---
name: fresh-vm
description: Prepare, verify, and reuse a spare cogatest VM for an attended human test on macOS or Windows. Use for install walks and competitor trials that need a known starting state.
---

# Prepare a fresh test computer

Use this guide together: the human prepares the test computer, and their
helper agent stays on their normal account and records the starting state.
The calling ticket or skill decides what to test and where to keep the
record. This guide owns VM setup, baseline, reuse, and cleanup for both
install walks and competitor trials.

A virtual machine (VM) runs in a window and behaves like a separate computer.
Your normal account already has tools installed, which would hide problems
a new user hits. Keep that account for talking to your helper.

## Choose the starting environment

Use a VM for a fresh-machine walk. A new user account on your own computer
inherits machine-wide installs, even when they are missing from its `PATH`:

- On macOS: Command Line Tools (so the Git install popup never appears),
  Homebrew under `/opt/homebrew` or `/usr/local`, and python.org Python under
  `/usr/local/bin`.
- On Windows: Git for Windows, an all-users Python, and machine-wide winget
  packages.

A new account can recheck a step that does not depend on those tools. Mark
prerequisite steps affected by inherited software as "machine-wide, not a
real test". Do not assume the other tools or sign-ins are absent: record what
is actually there. If a VM is unavailable, the ticket's fresh-machine check
remains untested; a new account supplies only partial evidence.

For a reused VM, skip creation and follow [Reusing a spare](#reusing-a-spare).

## Create a macOS guest in UTM

This route needs an Apple silicon Mac (M1 or later; check Apple menu → About
This Mac). An Intel Mac needs another suitable machine for the full walk;
a new account can supply only the partial checks above.

1. Check free space in System Settings → General → Storage. Allow **about
   45 GB at minimum, with extra headroom**. Earlier walks downloaded a
   15–18 GB restore image and used roughly 25 GB for the installed guest;
   versions and later installs change these sizes. A 64 GB virtual disk does
   not reserve all that space immediately.
2. Download the free **UTM** app from [its website](https://mac.getutm.app).
   Open `UTM.dmg`, then drag UTM into Applications. Open UTM with Cmd+Space,
   type `UTM`, Enter, and accept the macOS **Open** prompt. The disk icon on
   the desktop is the installer, not the app; eject it when finished.
3. Choose **Create a New Virtual Machine → Virtualize → macOS 12+**. Set
   memory to 8 GB (4 GB on an 8 GB host), CPUs to 4, and disk to 64 GB. Leave
   the restore-image field empty so UTM downloads a compatible macOS. The
   order of these wizard screens varies by version.
4. Save and start the VM. Complete the setup screens, skip Apple Account
   sign-in, and name the local user `cogatest`.
5. Run the [baseline](#baseline) inside the guest and send it to your helper.
   Then shut the guest down.
6. **On the host Mac**, delete the cached restore image before cloning. Open
   the host's Terminal and run:

   ```sh
   rm ~/Library/Containers/com.utmapp.UTM/Data/Library/Caches/*.ipsw
   ```

   This removes downloaded installer images, not the VM. UTM can download
   them again. The cache was about 18 GB in the observed walk; freeing it
   first prevents the working VM from filling the host disk later.
7. Right-click the stopped VM in UTM and choose **Clone**. Label the clone
   as the bare spare and keep it untouched. Run the original for this walk.
   On APFS the clone initially shares disk blocks, but free space falls as
   the working copy changes; keep checking the host's available storage.

The macOS guests used in the original walks could not take snapshots, so
this procedure uses Clone. Support depends on the macOS and UTM versions:
[UTM's guest-support page](https://docs.getutm.app/guest-support/macos/#missing-features)
lists the current restrictions. Record the versions instead of treating
"UTM cannot snapshot macOS" as a permanent rule.

### Moving commands and evidence

The original bare UTM guests had **no shared clipboard**. Copy commands from
the guest's own browser into its terminal. For extra commands or prompts,
the helper should provide a page or file the human can open inside the guest,
using the sharing tools available in the session. Check that it opens before
relying on it; no particular agent's artifact service is required.

[UTM supports clipboard sharing](https://docs.getutm.app/guest-support/macos/#clipboard-sharing)
when both sides run macOS 15 or later and the feature and guest tools are
configured. Do not assume that a bare guest has them. Record added guest
tools as setup changes. When paste back to the helper is unavailable, capture
the guest window from the host and send screenshots of the output. Mark any
manually transcribed evidence as such. Retyping errors in extra commands,
clipboard limitations, and host slowness are VM setup artifacts; keep them
separate from product findings.

## Create a Windows 11 guest in VirtualBox

1. On the Windows PC, install [VirtualBox](https://www.virtualbox.org) and
   download the [Windows 11 ISO](https://www.microsoft.com/software-download/windows11).
2. Choose **New**, select the ISO, and **tick Skip Unattended Installation**
   (or disable unattended setup in the installed version). Otherwise
   VirtualBox supplies an account and skips the setup screens this walk
   needs. See the [VirtualBox manual](https://www.virtualbox.org/manual/).
3. Set memory to 8 GB (4 GB on an 8 GB host), CPUs to 4, and disk to 64 GB.
   Start the VM and complete Windows setup for the edition named by the
   ticket. If setup offers **I don't have a product key**, it allows you to
   defer entering one; record the edition and activation state.
4. Follow the account setup offered by that Windows build. Use a local
   `cogatest` account if offered, or the human's designated test Microsoft
   account if required. Record which route was used without recording the
   account's address. Do not rely on `start ms-cxh:localonly`: Microsoft
   [announced removal of local-only setup commands](https://blogs.windows.com/windows-insider/2025/10/06/announcing-windows-11-insider-preview-build-26220-6772-dev-channel/)
   in newer builds. Account setup is preparation, not a Coga finding.
5. Run the [baseline](#baseline), then use **Machine → Take Snapshot** in
   VirtualBox. Label it as the bare starting point.

WSL or Hyper-V on the host can affect VM performance. Record the host setup
and separate VM slowness from evidence about the installed product.

## Baseline

Before installing tools, record the host/guest OS versions, VM application
version, chosen machine, and any setup additions. The human sends the full
output below to the helper as "Mac baseline" or "Windows baseline"; use the
capture route above if clipboard sharing is absent. Retain the baseline with
the walk's findings, redacting personal details.

**Mac:** open Terminal in the guest (Cmd+Space, type Terminal) and run:

```sh
sw_vers; uname -m; xcode-select -p; which -a git python3 brew uv coga claude codex gh
```

Do not run `git` or `python3` yet. On the observed bare Macs, `/usr/bin/git`
and `/usr/bin/python3` were Command Line Tools stubs that opened an install
popup. `which -a` locates them without running them; an error from
`xcode-select -p` is expected before the tools are installed. Let the actual
install walk reveal any popup naturally. Add the tool under test's command
names to the lookup when testing a competitor.

**Windows:** open PowerShell in the guest (Start, type PowerShell) and run:

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture
Get-ExecutionPolicy
Get-Command git,python,py,uv,coga,claude,codex,gh,winget -ErrorAction SilentlyContinue | Format-Table Name,Source
```

These commands inspect installed command paths without invoking Python's
app-execution alias. Add the tool under test to the command list as needed.
The baseline is evidence about visible tools, not proof that all leftovers
are absent; it accompanies the known bare clone or snapshot.

## Reusing a spare

At the start of every walk, confirm **which** machine is being used and that
it has **returned to bare**. Clone the untouched macOS spare and use that
new working copy, or restore the Windows baseline snapshot. Rerun the
baseline and compare it with the original. A VM previously used for another
trial may retain an agent CLI, a venv, and scratch projects even if the
product now being tested has never been installed.

If the human installs something from habit before the tested product asks
for it, record it as an operator step. It is not evidence that the product
requires that prerequisite.

## Rechecking in a new account

Use this only for the partial checks described under
[Choose the starting environment](#choose-the-starting-environment).

- **Mac:** System Settings → Users & Groups → Add User; create an
  administrator named `cogatest`, then log out and into that account.
- **Windows:** Settings → Accounts → Other users → Add account; choose
  **I don't have this person's sign-in information → Add a user without a
  Microsoft account**. Create `cogatest`, change its account type to
  Administrator, then sign out and into it.

Run the baseline and record the inherited tools before the recheck.

## Teardown

Once the findings are saved and the human has finished with the working
copy, delete it through UTM or VirtualBox and keep the bare spare for
retests. Remove a temporary `cogatest` user through Users & Groups or
Accounts only after its notes have been saved. Keep any VM the ticket still
needs for reproducing an unresolved finding.
