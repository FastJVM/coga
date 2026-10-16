# Testing the coga install: a guide for Zach

## What this is and why

We want to know what it feels like to install coga for the very first time.
You play the new user. Install it on a clean computer, following only the
public instructions, and write down everything you notice:

- **Does it work?** Did each step do what it said it would?
- **Lag.** Anything that takes a while, especially with nothing on screen to
  say it's working. A long wait with no feedback is exactly what we're after.
- **Weird stuff.** Confusing messages, words you don't know, popups or
  security warnings you didn't expect, steps where you had to guess, things
  that look broken or unprofessional even if they work.

There are no wrong answers. If something confused you, it will confuse other
people too, and that's a finding. You aren't being tested; the installer is.

You do this twice: once on the Mac, once on Windows. Do the Mac first.

If you test with both a VM and a new user account, do the VM walk first and
do it cold. Whichever walk you do first is the only one that captures your
genuine first reaction. After that you know the answers, and the confusion we
are looking for is gone.

## What you need

- Your Mac and your Windows PC.
- About 2–3 hours per computer the first time (most of it is downloads).
- Your normal account with Claude Code open in the coga folder. This is your
  helper: when you're stuck, or want to report something, tell it there.
  Keep this separate from the clean computer.
- A notes file or a sheet of paper, and a clock or stopwatch.

## Part 1: Get a clean computer

Your normal account already has coga and its tools installed, so testing
there would hide the problems a new user hits. Instead, make a brand-new
computer inside your computer (a *virtual machine*, or VM). It runs in a
window and is like a Mac or PC fresh out of the box. Deleting it later
leaves your real computer untouched.

### On the Mac

First check what chip you have: Apple menu → About This Mac. If it says
**M1, M2, M3, M4** (or later), follow "Option A". If it says **Intel**,
follow "Option B".

**Option A: a fresh Mac in a window (preferred)**

First check you have room: Apple menu → About This Mac → More Info →
Storage. You need about 45 GB free. The VM grows to roughly 25 GB once macOS
is installed, on top of the 15 GB download, even though you set its disk size
to 64 GB.

1. Download **UTM** (free) from https://mac.getutm.app — the grey
   **Download** button, not the $9.99 Mac App Store one. They are the same
   app. Double-click the downloaded `UTM.dmg`, then drag the UTM icon onto
   the Applications folder shown next to it.

   The UTM icon left on your desktop afterwards is the installer disk, not
   the app, and clicking it does nothing. Open the real app with Cmd+Space,
   type `UTM`, Enter; click **Open** if macOS asks about an app downloaded
   from the internet. Right-click the desktop icon → **Eject "UTM"** to
   clear it.
2. Click **Create a New Virtual Machine** → **Virtualize** → **macOS 12+**.
3. Leave the install file empty so UTM downloads the latest macOS for you
   (about 15 GB; this is the slow part).
4. Memory: 8 GB (or 4 GB if your Mac only has 8 GB). CPU: 4. Disk: 64 GB.
   Save.
5. Press play. Go through the setup screens like a new Mac. **Skip the Apple
   ID** sign-in. Name the user `cogatest`.
6. Do Part 2 (the baseline) and paste it to your helper.
7. Shut the VM down. **Delete the macOS installer UTM downloaded** — about
   18 GB you need back. It is a cache and UTM re-fetches it if ever needed:

   ```
   rm ~/Library/Containers/com.utmapp.UTM/Data/Library/Caches/*.ipsw
   ```

   Then right-click the VM in UTM and choose **Clone**. The clone is your
   spare clean copy for later re-tests. Run the original, not the clone.

   Cloning is nearly free at first: the Mac's filesystem shares the blocks
   rather than copying 26 GB, so free space barely moves. It only grows as
   the working copy changes during the walk. Measured on a 2026-10-15 run.

Do step 7 in that order. Cloning before you delete the installer can fill
your disk partway through the walk, which looks like a coga failure and costs
you the afternoon.

**Option B: a fresh user account (Intel Mac, if A fails, or for re-tests)**

1. System Settings → Users & Groups → **Add User…**
2. Type: Administrator. Name: `cogatest`. Set a password.
3. Log out of your account (Apple menu → Log Out) and log in as `cogatest`.

A new account is instant and uses no disk, which makes it the right place to
re-test a single step after we fix something.

It is not as clean as the VM. Two steps will look easier than they really
are: `git` will already work, and `python3` will already be a new enough
version, because both are installed for the whole machine rather than per
account. On a real fresh Mac, `git` opens an install popup and `python3` is
too old for coga. If you use Option B, write "already installed on this
machine, not a real test" next to those two steps instead of "worked fine".
Everything else is genuinely clean: no `uv`, no `brew`, no `coga`, no
`claude`, no `gh`, and no sign-ins.

### On Windows

**Option A: a fresh Windows in a window (preferred)**

1. Download **VirtualBox** (free) from https://www.virtualbox.org and
   install it.
2. Download the Windows 11 disk image (ISO) from
   https://www.microsoft.com/software-download/windows11 (section "Download
   Windows 11 Disk Image (ISO)").
3. In VirtualBox click **New**, pick the ISO, and **tick "Skip Unattended
   Installation"**. This matters: without it, VirtualBox skips the setup
   screens we want to see.
4. Memory: 8 GB (or 4 GB if your PC only has 8 GB). CPUs: 4. Disk: 64 GB.
   Finish and press Start.
5. In Windows setup, when asked for a product key, click **I don't have a
   product key** and pick **Windows 11 Home**. It works fine without one.
6. When it asks you to connect to a network or sign in with Microsoft, press
   **Shift+F10**. In the black window that opens, type
   `start ms-cxh:localonly` and press Enter, then create a local user called
   `cogatest`. If that doesn't work, sign in with a throwaway Microsoft
   account and write down that you did.
7. Do Part 2 (the baseline). Then in VirtualBox: Machine → **Take
   Snapshot**, so you can go back to clean later.

It may be slow if your PC also runs Linux (WSL). That's expected and not a
coga finding.

**Option B: a fresh user account (if A is too slow or fails)**

1. Settings → Accounts → Other users → **Add account**.
2. Click **I don't have this person's sign-in information**, then **Add a
   user without a Microsoft account**. Name: `cogatest`.
3. Click the new account → **Change account type** → Administrator.
4. Sign out and sign in as `cogatest`.

Mention in your notes that you used Option B.

## Part 2: Take a "before" snapshot (2 minutes)

This records what's on the clean computer before you install anything, so we
can tell coga problems apart from leftovers. Copy the command, paste it,
press Enter, and paste the whole output to your helper (Claude) with
"Mac baseline" or "Windows baseline".

**Mac:** open Terminal (Cmd+Space, type Terminal) and run:

```
sw_vers; uname -m; xcode-select -p; which -a git python3 brew uv coga claude gh
```

Don't type `git` or `python3` on their own yet. On a fresh Mac they open an
install popup, and we want to see that happen naturally later.

**Windows:** open PowerShell (Start, type PowerShell) and run:

```
[Environment]::OSVersion; Get-ExecutionPolicy; Get-Command git,python,py,uv,coga,claude,gh,winget -ErrorAction SilentlyContinue | Format-Table Name,Source
```

## Part 3: Install coga like a new user

On the clean computer, open a web browser and go to
**https://github.com/FastJVM/coga**. From here on, **only follow what the
page tells you.** Don't use what you already know about coga. If the page
doesn't say how to do something, that's a finding: write it down, then ask
your helper.

You should get through roughly these steps, in whatever words the page uses:

| # | Step | It worked if… |
|---|------|---------------|
| 1 | Install the tools coga needs (Python, uv, git…) | the page's check command prints a version |
| 2 | Install coga (`uv tool install coga`) | `coga --version` prints a version |
| 3 | Make a folder for a project and run `coga init` in it | it finishes without an error |
| 4 | Install and sign in to an AI agent (Claude Code) if asked | the agent starts |
| 5 | Run `coga build` and answer its questions | it gets through its first step |
| 6 | Create a first ticket with `coga ticket "Write a hello-world script"` | you end up with a ticket file |

**On Windows**, we already know coga is likely to fail at step 2 with an
error mentioning `fcntl`. That's expected. Write down everything up to that
point (how hard it was to get Python and uv, any warnings), paste the error
to your helper, and stop there.

### For every step, write down

```
Step:        (number and what you were doing)
Command:     (what you typed or clicked)
Time:        (start → finish; note any wait over ~10 seconds)
What I saw:  (copy the message, or take a screenshot)
What I expected:
Weird / confusing / slow?:
Did I need help?: (yes/no; what you asked)
```

Screenshots are great: Cmd+Shift+4 on Mac, Win+Shift+S on Windows.

## Part 4: When something goes wrong

1. Don't try to fix it yourself with tricks you know. A real new user
   wouldn't know them either.
2. Copy the full error text (or screenshot it) and paste it to your helper
   (Claude, on your normal account) with one line about what you were doing.
3. The helper records it as a finding and either tells you how to get past
   it or fixes coga. If it fixes coga, you may be asked to redo that step on
   a fresh copy (the clone on Mac, the snapshot on Windows).

## Part 5: When you're done

Tell your helper "Mac walk done" (or Windows) and give it your notes. Then
answer three quick questions:

1. What was the single most annoying moment?
2. Was there a point where you'd have given up if this weren't your job?
3. Overall, how long did it take, start to finish?

You can delete the VM afterwards (UTM or VirtualBox: right-click → Delete),
or keep it for re-tests. If you used a new user account, you can remove it
from Users & Groups / Accounts once we're done.
