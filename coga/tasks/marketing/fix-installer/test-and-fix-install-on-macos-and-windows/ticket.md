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
2. confirmed by walk — Nothing gives a fresh machine a route to `uv` or
   Python 3.11. The README opens with `uv tool install coga`;
   `coga/install` links uv's homepage without an install command and says
   "Install Python 3.11+ separately (`uv tool install` can manage its own
   Python)", which is circular when neither is present. Reproduced on the
   guest 2026-10-15, copying the command from the README's own code block:

   ```
   % uv tool install coga
   zsh: command not found: uv
   ```

   The first command the public page gives a new user fails on a clean
   machine. The documented recovery path fails too: the README's "Install"
   link leads to `coga/install`, which links uv's homepage without an
   install command. All four routes that topic offers dead-end on a fresh
   Mac — `uv` and `pipx` are absent with no acquisition instructions, and
   both `python3` routes hit the CLT stub and then Python 3.9, under the
   3.11 floor. Completing step one requires leaving Coga's documentation
   for a third-party site.

   The handoff to that site then fails three ways, walked 2026-10-15. The
   link is a bare `uv` inside a sentence with no statement that it must be
   installed, so the requirement is inferred rather than told. It targets
   `https://docs.astral.sh/uv/`, the project root, landing the reader on
   Introduction rather than the installation page. And that page offers
   nine methods — standalone, PyPI, Homebrew, MacPorts, WinGet, Scoop,
   Docker, GitHub Releases, Cargo — of which only the standalone `curl`
   installer works from nothing; PyPI needs the absent Python, Homebrew and
   MacPorts need a package manager the user lacks, and Cargo needs Rust.
   Several documented doors lead back to the problem being escaped. uv's
   docs are not at fault: they address readers who already know their
   package manager. Coga delegated a mandatory step without naming the
   door, so its own page should carry the command.

6. open — `uv tool install coga` itself springs the Command Line Tools
   trap, which no surface predicts. On the guest 2026-10-15 the install
   compiled a dependency from source (`Built pyyaml==6.0.3` among 19
   packages) and macOS raised "The `python3` command requires the command
   line developer tools. Would you like to install the tools now?".
   `coga/install` documents this trap but attributes it to `git` and tells
   the reader to install the tools before `git init` or `coga init`; it
   does not say the package install can trigger it. The README names no
   Command Line Tools requirement at all, so a reader following the public
   page meets an unexplained system dialog mid-install.

   The install still completed and reported `coga 0.4.0`, because pyyaml
   falls back to a pure-Python build. The severity is therefore an
   unexplained interruption on a desktop, but a hard stop anywhere no
   dialog can be shown, which is the same class of failure the topic's own
   headless SSH section describes. The Apple download that follows the
   dialog ran over 17 minutes on this host, which nothing in the README or
   the topic prepares the reader for.

7. open — the root cause of finding 6 is Coga's own packaging: an
   unbounded Python floor. `pyproject.toml` declares
   `requires-python = ">=3.11"` with no ceiling, so `uv tool install coga`
   on a machine with no Python resolves the newest interpreter available
   and installed CPython 3.15.0 on the guest. Dependencies have not shipped
   3.15 wheels yet, so uv built PyYAML from source, and a source build of a
   C extension needs the compiler a fresh Mac lacks. uv also warned on that
   interpreter: "Failed to patch the install name of the dynamic library
   for `…/cpython-3.15.0-macos-aarch64-none/bin/python3.15`. This may cause
   issues when building Python native extensions."

   This is a packaging finding rather than a documentation one, and it is
   deterministic: every clean-machine install takes this path until the
   dependency set publishes 3.15 wheels. Two fixes, both with a cost, and
   the choice is the owner's. Capping `requires-python` (for example
   `>=3.11,<3.15`) repairs the default command but commits the project to
   raising the cap as each Python release is validated and locks out users
   already on the newest interpreter. Pinning in the documented command
   (`uv tool install --python 3.12 coga`) changes no packaging but leaves
   the plain command broken for anyone not copying that exact line.
   Recommend the cap, because the defect is that the default path fails.

8. open — `coga init`'s offer to install missing external CLIs cannot fire
   on a fresh Mac, which is the machine it was built for. On the guest
   2026-10-15 init printed only links:

   ```
   Optional tools not on PATH (init continues without them):
     - gh: install from https://cli.github.com
     - op: install from https://developer.1password.com/docs/cli/get-started/
   ```

   `_offer_install` in `src/coga/commands/init.py` returns early unless the
   detected package manager appears in the dependency's `packages` map, and
   `src/coga/dependencies.py` keys those on brew, winget, apt-get, dnf and
   pacman. macOS ships none of them, so a Mac without Homebrew always takes
   the printed-link fallback. `coga/install` documents the fallback, so the
   behavior is correct; the gap is that the feature's reach excludes its
   intended audience. The owner reversal of 2026-09-30 recorded in that
   topic motivates the offer by users reading a missing `gh` as a broken,
   unprofessional install and churning, which is the fresh-machine user who
   cannot receive it. Worth deciding whether init should offer to install
   Homebrew first, or whether the printed-link path deserves the attention
   instead.

9. open question for the owner, not a defect — `coga init`'s next steps
   name actions without the shell knowledge to perform them: it gives the
   `gh` and `op` install links without saying how to get them on PATH
   afterwards, and the exact Slack TOML with `then export
   SLACK_WEBHOOK_URL` without saying where an export belongs so it
   survives a new terminal. Raised by the owner during the walk. Whether
   this is a gap depends on positioning: the README addresses "small
   technical teams who already use CLI agents, are comfortable with Git and
   the shell", under which assuming it is defensible. Needs a positioning
   call before any documentation change.

5. open — `coga/install` describes its prerequisites instead of supplying
   them, and the gap falls exactly on the blocking ones. Of its six
   prerequisites only Git is genuinely taught, through the CLT section; the
   agent CLI, `gh` and `op` are delegated to `coga init`'s install offers.
   Python 3.11+ and `uv`, the two that actually stop an install, get a
   failure-mode description and a hyperlink. Its advice is circular for the
   stuck reader: "Install Python 3.11+ separately (`uv tool install` can
   manage its own Python)" presumes the `uv` the reader does not have.

   Owner's verdict on reading it as a new user, 2026-10-15: "The page is
   called install, but it doesn't really answer anything about an easy way
   to get these tools. They're all serving as definitions or explanations,
   how they might behave in certain situations, with literally no reference
   to how to get them."

   Root cause is a dual audience, not carelessness. The file is a context
   under `docs/contexts/`, written as the agent-facing contract where
   internals like the `fcntl` import and `_require_init_tools` belong, and
   the README links it as the human install guide. Proposed fix keeps the
   explanation and adds the missing instructions: a README block that runs
   from nothing (install `uv`, which brings its own Python; then coga; then
   create a repo; then init), and an acquisition section at the top of the
   topic ahead of the rationale. Not a documentation restructure.
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

### What this walk does and does not measure

Elapsed times are not recorded. The walk is conversational, with the owner
pausing to report and take breaks, so wall-clock numbers would look like
data without being data. What the walk establishes is the sequence of what
blocked a new user and what it took to get past it; the guide's stopwatch
column is unreliable under this format and should not be read as timing
evidence.

### Guest constraint affecting the walk record

UTM shares no clipboard with a macOS guest, so host-to-guest paste does not
work. The walk itself is unaffected because Zach copies from the guest's own
Safari into the guest's Terminal, which is what a real user does. Only
out-of-band commands are retyped, so a typo in one of those is a VM artifact
and not a finding.

### Walk findings

4. confirmed by walk, low severity — The README's install block assumes a
   git repository already
   exists and never says how to make one. Its third line is
   `cd <your git repository>`, with no preceding `mkdir`/`git init`, so a
   first-time user on a fresh machine has nothing to change into. "First
   steps" then branches on "Empty repo" versus "Existing project", which
   shows an empty repo is an expected starting point, yet no surface tells
   the user to create it. Raised by Zach unprompted before reaching the step,
   which is itself the evidence: the sequence reads as incomplete to a new
   user. `README.md` install block owns the fix; `coga/init` may need the
   same entry point.

   Reproduced on the guest 2026-10-15 after following the block exactly.
   The owner had to invent the project folder himself, then:

   ```
   % coga init --user zach
   /Users/cogatest/Desktop/cogatest is not inside a git repository — coga
   is git-backed.
   Run `git init` in /Users/cogatest/Desktop/cogatest (or an ancestor)
   first, then re-run `coga init`.
   ```

   Rated low severity deliberately, because the product recovers where the
   documentation failed: the error names the cause, the exact command and
   the follow-up, so a reader is unstuck in seconds. The defect is that the
   documented happy path does not run, not that the failure is hard to
   escape. Contrast finding 2, where `command not found: uv` explains
   nothing and the documented recovery leads off-site. Fix is one line in
   the README block; the error message needs no change.

## New-user walk: macOS — run 2

Started 2026-10-17 on a sealed clone of the post-baseline spare, so the
machine state matches run 1's baseline exactly: no Command Line Tools, no
`uv`, no `coga`, `/usr/bin/git` and `/usr/bin/python3` as stubs.

Installing from PyPI with the plain `uv tool install coga`, as a real user
would. No fix has been merged yet, so this is a reproduction rather than a
verification; the ticket's install-from-main route is for the later
fix-verification run.

Scope, agreed with the owner after he was told run 1 already holds evidence
for steps 1-4: run 2 can establish that those failures reproduce
deterministically on an untouched machine, and can capture first-time
reactions to `coga build` and the first ticket, which run 1 never reached.
It cannot produce fresh human signal on steps 1-4, because the same walker
now knows the answers.

Findings carry run 1's numbers where they reproduce; genuinely new ones
continue from 10.

### Run 2 findings

(not started)

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
