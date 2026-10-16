---
title: Test and fix install on macOS and Windows
status: in_progress
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
on a fresh macOS and a fresh Windows environment on his own hardware
(following `guide-for-zach.md`, attached), the way a first-time user would: follow the README / `coga/install` docs only, then
`uv tool install coga`, `coga init`, `coga build`, and a first `coga ticket`.
The agent session (run from Zach's usual coga checkout, not inside the fresh
environment) records every point where he gets stuck, confused, or has to
guess, and fixes what it can in the same session.

Known going in: on macOS, the Xcode Command Line Tools git stub and the
system Python 3.9 (below the 3.11 floor). Native Windows does not start at
all: `coga.git` imports `fcntl` at module top, so even `coga --help` fails,
and `repl_supervisor` / `megalaunch` need pty/termios/tty. The deep Windows
port is `windows-native/core-port-cli-and-test-suite-pass-on-native-window` (owner decision 2026-10-13); this
ticket feeds it findings and does not duplicate it.

Done when: both walks are done and their findings are listed per OS on the
blackboard (each tagged fixed-in-PR, tracked-elsewhere, or open); fixes that
fit this ticket are merged as PRs; and `docs/contexts/coga/install/SKILL.md`
says, step by step, what Zach ran and saw on each OS, including the
fresh-environment setup from the guide if it proved useful. Windows is expected to stop
at `coga --help` (`fcntl`); for Windows, done means the findings up to that
point are recorded and handed to `windows-native/core-port-cli-and-test-suite-pass-on-native-window`, not that
coga runs there.

## Context

### Zach's guide (attachment)

Zach is not an engineer. He follows `guide-for-zach.md` beside this ticket:
plain-language steps to make a fresh VM (UTM macOS VM on Apple Silicon,
VirtualBox Windows 11 VM) or, as fallback B, a new `cogatest` user account;
a baseline command; the install walk from the public README; a per-step note
template (command, time, what he saw vs expected, weird/slow, needed help);
and three wrap-up questions. The goal is human signal: lag (waits with no
feedback), idiosyncrasies (confusing text, surprise popups/warnings, guessed
steps), and whether each step works. Keep the guide in sync if the walk
changes, and fold what proves useful into `coga/install`.

Agent-side facts the guide simplifies:

- Option B (new user account) leaks machine-wide installs: on macOS the CLT
  (git stub won't appear), Homebrew under `/opt/homebrew`, python.org Python
  in `/usr/local/bin`; on Windows, Git for Windows, "all users" Python,
  machine-wide winget packages. Flag findings that depend on these.
- On a fresh Mac both `/usr/bin/git` and `/usr/bin/python3` are CLT stubs;
  Python 3.9 appears only after CLT installs. The baseline avoids invoking
  them.
- UTM cannot snapshot macOS guests (the guide uses Clone); VirtualBox needs
  "Skip Unattended Installation" or it bypasses OOBE and creates `vboxuser`.
- Zach pastes baselines and errors into this session; record them on the
  blackboard under the matching walk section.

### Walk rules

- Zach acts as a new user: docs only, no help from the agent unless he is
  stuck, and a needed hint is itself a finding.
- Per step, note: the exact command, what happened, what he expected, and
  how long he was stuck.
- Fix loop: finding -> PR -> merge -> re-walk the affected step in a fresh
  environment (VM clone/snapshot taken right after the baseline, or a new
  user account). `uv tool install coga` installs from PyPI, so a merged fix
  is not there until a release. For a re-walk, install from main instead:
  `uv tool install git+https://github.com/FastJVM/coga@main`, and note in
  the finding that it was checked against main, not a release. Doc-only fixes
  need no reinstall.
- `coga/testing/clean-install/macos-aws` already covers the automated
  fresh-Mac harness on EC2; this ticket is the human counterpart and does not
  rent machines.
- Repo is public: no account IDs, emails or keys on the blackboard.

<!-- coga:blackboard -->
# Test and fix install on macOS and Windows

## Dev

branch: install-walk-findings

## Plan (2026-10-15, attended)

Owner chose the UTM VM as the primary macOS environment because it is the
most faithful, with a new `cogatest` user account as the cheap re-walk
environment after fixes. The VM walk goes first and cold. Order: VM walk ->
findings -> fixes -> re-walk fixed steps in a new user account -> Windows
walk -> update `coga/install`.

Decision: the doc fixes below are held until after the macOS walk, so Zach
hits the same docs a real new user hits today. If he gets stuck where
finding 1-3 predicts, the walk confirms them; if he sails past, the reading
was wrong.

## Host facts (Zach's Mac, 2026-10-15)

- Apple M2, arm64, so the guide's UTM route applies. UTM not installed at
  session start. 65 GiB free of 228 GiB.
- That is enough for one VM but not for a clone unless the 15 GB installer is
  deleted first. The guide now sequences baseline -> delete installer ->
  clone -> walk.
- Machine-wide, so invisible to a new user account: Xcode CLT at
  `/Library/Developer/CommandLineTools`, making `/usr/bin/git` real git; and
  python.org Python 3.13 in `/usr/local/bin`, which is on every account's
  default PATH from `/etc/paths`, along with node and npm.
- Per-user, so genuinely clean in a new account: `uv`, `brew`, `claude`,
  `gh`, git identity and agent logins. All resolve from `/opt/homebrew/bin`,
  which a new account's PATH lacks because `~/.zprofile` adds it.
- Consequence: a new user account cannot reproduce the git-popup or
  Python-floor steps. Both are already documented in `coga/install`, so the
  walk does not need to rediscover them.

## Pre-walk findings (from the docs, no walk needed)

1. open — `README.md:116` says "Coga runs on Linux, Windows or macOS", while
   `coga/install` says native Windows is unsupported because `coga.git`
   imports `fcntl` at module top, so even `coga --help` fails. The guide
   sends the new user to the README alone, so the README is what walks a
   Windows user into the crash. The claim entered in `cc9c54e9c` ("Revise
   README for clarity"), not from any Windows-support decision.
2. open — Nothing gives a fresh machine a route to `uv` or Python 3.11. The
   README opens with `uv tool install coga`; `coga/install` links uv's
   homepage without an install command and says "Install Python 3.11+
   separately (`uv tool install` can manage its own Python)", which is
   circular when neither is present. On a fresh Mac this is `command not
   found: uv`.
3. open — The macOS Command Line Tools prerequisite is absent from the
   README, which says only "needs ... Git". `coga/install` owns the detail
   including the headless route.

## Carried-over finding — answered, close it

- The CRLF worry does not reach installed users. `launch_script.py` runs the
  deterministic phase as `[sys.executable, str(entry)]`, so a `ticket.py`
  shebang is never used, and no `.sh` ships under `src/coga/resources/`. The
  breakage was confined to this checkout's `scripts/clean-install/` dev
  scripts, which an installed user never touches.

## New-user walk: macOS

In progress 2026-10-15, UTM VM on Zach's M2, guest macOS 26.6.2.

### VM setup (scaffolding, not coga findings)

Recorded because the ticket asks whether the guide's fresh-environment setup
proved useful. These are UTM and Apple frictions, not coga's.

- About 35 minutes from opening the UTM download page to a booting guest, of
  which the 18 GB image fetch was ~10 and the install ~20. Faster than the
  guide's 2-3 hour estimate.
- Three guide gaps hit and fixed in place: the downloaded `.dmg` needs a
  double-click and the leftover desktop icon is the installer disk rather
  than the app; the cached image path for the reclaim step; and the order of
  reclaim before clone.
- Disk is the real constraint and the guide's "about 45 GB free" is right but
  has no margin. Peak usage was the 18 GB image plus a 22 GB guest against 65
  GB free, leaving 19 GB.
- UTM's wizard orders its screens differently from the guide: the image
  prompt comes after hardware and storage, not before. Leaving it empty is
  correct and the dialog says so.

### Baseline (guest, before any install)

```
ProductName:     macOS
ProductVersion:  26.6.2
BuildVersion:    25G83
arm64
xcode-select: error: Unable to get active developer directory. Use `sudo
xcode-select --switch path/to/Xcode.app` to set one (or see `man xcode-select`)
/usr/bin/git
/usr/bin/python3
```

Confirms `coga/install`'s premise on a real fresh Mac rather than by
assertion: no Command Line Tools, so `/usr/bin/git` and `/usr/bin/python3`
are stubs; and no `brew`, `uv`, `coga`, `claude` or `gh` anywhere.

### Guest constraint affecting the walk record

UTM shares no clipboard with a macOS guest, so host-to-guest paste does not
work. The walk itself is unaffected because Zach copies from the guest's own
Safari into the guest's Terminal, which is what a real user does. Only
out-of-band commands are retyped, so a typo in one of those is a VM artifact
and not a finding.

### Walk findings

(walk begins when the guest opens the public README)

## New-user walk: Windows

(not started)

## Blockers

- [x] [2026-10-14 13:19] [agent:claude] id=20261014T131919 Needs an attended session on Zach's own Mac and Windows machines: the ticket is a hands-on clean-install walk (uv tool install coga, coga init, coga build, first ticket) on those machines, which this queued Linux session cannot reach. Relaunch it attended on the Mac, then on Windows. The Windows fcntl port is tracked separately in make-coga-run-on-native-windows.
  resolved: [2026-10-14 16:45] [human:zach] Owner chose rented disposable AWS macOS and Windows hosts; the read-only Mac preflight is green, so the old own-machine attendance premise no longer blocks the ticket.

## Superseded designs

- 2026-10-14: walk on rented AWS hosts (EC2 Mac and EC2 Windows Server).
  Dropped on 2026-10-15 because this ticket is the human counterpart to the
  automated harnesses. No AWS host was allocated and nothing was spent. The
  setup log, cost notes and removal steps now live in Zach's private admin
  repo (ticket `ops/aws-rented-machine-coga-install-testing`), not here.
