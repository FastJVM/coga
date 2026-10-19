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
step: 3 (pr)
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

Windows moved out on 2026-10-18 (owner). This ticket is macOS only; the
title predates the split. The Windows walk is
`marketing/fix-installer/test-install-on-windows`, deferred until the port
lands because a walk today tests a path that cannot work at all.

Done when: the macOS walk is done and its findings are listed on the
blackboard (each tagged fixed-in-PR, tracked-elsewhere, or open); fixes that
fit this ticket are merged as PRs; and the README carries clear install
instructions in no more than five lines. `docs/contexts/coga/install` is
being deleted (owner, 2026-10-17), so the blackboard also lists the facts
from it that are candidates for a surviving context — proposals for review,
not commitments.

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

## Owner decision, 2026-10-17: delete `coga/install`

The install topic is being removed and the install instructions become no
more than five lines in the README. This changes what most findings fix.
Findings 2, 3, 11 and 12 become requirements on the new README lines rather
than repairs to the topic, and finding 5 largely dissolves because the page
it describes will not exist. Finding 13 survives in reduced form: whatever
those lines say must describe what PyPI serves, not `main`.

Facts the topic currently owns that would otherwise have no home. Listed as
candidates for a surviving context, for review rather than as commitments:

- The macOS Command Line Tools trap, including the headless
  `softwareupdate` route, and that the CLT ships Python 3.9.
- Why the floor is Python 3.11: config loading uses `tomllib`, and what an
  older interpreter fails with.
- Why native Windows does not run: `coga.git` imports `fcntl` at module
  top and `cli.py` imports `coga.git` eagerly, so even `coga --help` fails,
  and WSL is the untested route. Overlaps
  `windows-native/core-port-cli-and-test-suite-pass-on-native-window`.
- The `--require-hashes` install failure and its two workarounds.
- Which external CLIs are checked when, and that `coga init` enforces only
  `git`.
- The upgrade and removal commands per installer.

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

   All four routes now carry terminal evidence rather than analysis. The
   pip and pipx alternatives were walked on a fresh clone 2026-10-18:

   ```
   % pipx install coga
   zsh: command not found: pipx
   % python3 -m pip install coga
   xcode-select: note: No developer tools were found, requesting install.
   ```

   `pipx` gives the same bare `command not found` as `uv`. The `python3`
   route reaches Apple's Command Line Tools dialog, so the documented
   alternative meets the same trap as the primary route, by a different
   path; its message is more descriptive but it is Apple's, and says
   nothing about installing Coga. The fourth route, the venv one, shares
   `python3` and therefore the same blocker.

   One documented consequence no longer holds. `coga/install` warns that
   pip "may succeed at installing the old `0.0.1` placeholder, which
   provides no `coga` command". PyPI lists 0.0.1, 0.2.0 and 0.4.0, and
   0.0.1 is yanked with the note "Placeholder release with no coga CLI.
   Its Python >=3.9 metadata causes pip on Python <3.11 to install an
   unusable package." Yanked releases are not selected by default, so the
   silent broken install is already fixed. Correct that fact before
   extracting it anywhere.

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

Steps 1-4 reproduced exactly: `command not found: uv`, the uv link landing
on Introduction rather than Installation, the Command Line Tools dialog
during `uv tool install coga`, and `coga init` failing outside a git
repository. Findings 2, 4, 6 and 7 are therefore deterministic, not
first-run flukes. The owner's own notes are the primary record; the new
material follows.

10. open — `coga init`'s "Next steps" opens by telling the user to set
    configuration that `coga init` already set, and orders it ahead of the
    step that is actually required. Step 1 is "Edit `coga.toml` — set your
    agents, notification channels, and aliases", but the shipped template
    writes complete `[agents.claude]` and `[agents.codex]` tables, and
    `default_agent` is deliberately commented with "Unset, it's the first
    `[agents.*]` table below", so Claude is already the default and the
    file needs no edit. Step 2, installing an agent CLI, is the one the
    user cannot skip. A new user reads step 1, opens a 200-line config and
    searches for work that does not exist. Fix is to reorder and to say
    the config is complete unless the user wants Codex as default.

11. open — on a fresh Mac nothing opens `coga.toml`. No application is
    associated with `.toml`, so "Edit `coga.toml`" has no starting move for
    a user who has never installed an editor. Raised by the owner during
    run 2; invisible on any machine that has ever had one. Worth deciding
    whether init should name an editor that ships with macOS, or print the
    path in a form the user can act on.

12. open — the README never links `coga/uninstall`. The topic exists and is
    reachable only from the bottom of `coga/install`, so a user evaluating
    Coga cannot easily find out how to remove it. Owner proposes linking it
    from the README near the install section. Low cost, and relevant to a
    first-time evaluator deciding whether to try it at all.

13. open — the public documentation describes behavior absent from the
    released package, so a new user reads docs for software they cannot
    install. `uv tool install coga` ships 0.4.0; the docs on `main`
    describe 0.4.1. `coga/install` states that "`coga build`, when the
    onboarding ticket's agent CLI is missing, offers that one before
    failing", and `src/coga/launch.py` does call `offer_agent_cli` for the
    `coga-build` onboarding slug — but `src/coga/agent_cli_setup.py` does
    not exist in v0.4.0 at all, and `git show v0.4.0:src/coga/launch.py`
    contains no reference to it. It arrived after the tag, in
    `06df6cf18`. Reproduced on the guest 2026-10-17:

    ```
    % coga build
    → coga launch coga-build
    Launch: agent claude -> claude (cli=claude)
    Agent CLI 'claude' not found in PATH. Install it from
    https://claude.com/claude-code and authenticate, then re-run.
    ```

    No offer, because the released version has none. The README already
    concedes this drift in one place — the demo link notes "some command
    names may have changed since" — but nowhere does any surface say which
    release the documentation describes. Fix is a decision about whether
    docs track the release or `main`, and saying so on the page; the
    install instructions in particular should match what PyPI serves.
    Note the released-versus-main gap also governs the ticket's own
    re-walk rule, which installs from `main` to verify merged fixes.

14. open, contingent on 13 — on `main` the same step still cannot install
    an agent CLI on a fresh Mac. `installer_argv` in
    `src/coga/agent_cli_setup.py` returns None unless brew is present on
    darwin or `npm` is on PATH, so the offer degrades to printing the
    install URL. Finding 8's package-manager wall therefore blocks both
    places Coga promises to set a new user up: `gh` at init and the agent
    CLI at build. Whatever is decided for 8 should cover this path too.

15. open, highest severity so far — following Coga's own link does not
    produce the binary Coga requires, so the walk cannot be completed from
    the documented instructions. `coga build` fails with "Agent CLI
    'claude' not found in PATH. Install it from
    https://claude.com/claude-code and authenticate, then re-run." On the
    guest 2026-10-17 the owner followed that link, downloaded the `.dmg`
    and dragged Claude into Applications. `claude` is still not on PATH and
    no `claude` command runs. The page serves the desktop application;
    Coga drives the command-line tool.

    Taken with 13 and 14, no documented route reaches a working
    `coga build` on a fresh Mac. The build-time offer does not exist in the
    released version; on `main` it needs brew or npm, neither of which a
    fresh Mac has; and the printed link yields an app without the command.
    Routes that do work — install Homebrew first, or install Node and use
    `npm install -g @anthropic-ai/claude-code` — appear on no Coga surface.
    The error also says "and authenticate" without saying how or what
    success looks like, which was the owner's first observation here.

    Checked and confirmed absolute 2026-10-17: the owner opened the
    application, which is only the desktop app and installs no CLI, then
    re-ran `coga build` and got the identical error. The documented path
    from a fresh Mac to a working `coga build` does not exist.

16. open — Coga's dependency manifest does not know the agent CLI's
    recommended installer, which is the one that works without a package
    manager. `src/coga/dependencies.py` offers `claude` only through brew
    and npm, but Anthropic documents a native installer as the recommended
    macOS route, `curl -fsSL https://claude.ai/install.sh | bash`, needing
    neither Node nor Homebrew. The npm package downloads the same binary.
    Knowing it would close finding 15 and most of 14.

    This collides with a deliberate policy: `src/coga/agent_cli_setup.py`
    states "The installer is the vendor's package, never a `curl | sh`
    script." The script in question is the vendor's own documented and
    recommended method, so the supply-chain rationale is weaker here than
    the rule's wording implies — but relaxing it is the owner's call, and
    the current stance is precisely what leaves a fresh Mac with no route
    to an agent CLI.

### Proposed five-line README install, drafted 2026-10-17

Meets the revised Done-when. Verified step by step on the guest except the
agent CLI line, which replaces the Node detour the owner was unblocked with.

```sh
xcode-select --install                             # Apple's dev tools (gives git)
curl -LsSf https://astral.sh/uv/install.sh | sh    # then open a new terminal
uv tool install coga
curl -fsSL https://claude.ai/install.sh | bash     # then run: claude   (signs in)
mkdir myproject && cd myproject && git init && coga init --user <your-name>
```

Ordering the Command Line Tools first removes finding 6's mid-install
dialog, because the compiler is present before any source build. It masks
finding 7 rather than fixing it: a user with git but no compiler still hits
the 3.15 source build, so the `requires-python` cap remains worth doing.
Line 4 depends on the policy ruling in finding 16.

Owner's open questions for Nico, carried from his notes rather than
resolved here:

- Whether `coga init` should install `gh` itself while leaving `op`
  optional and outside init. Bears directly on finding 8.
- Whether the `cd <your git repository>` step needs explaining at all,
  given the README targets teams already comfortable with Git. Bears on
  finding 4's severity.

## Verification run: the proposed five lines

Started 2026-10-17 on a third sealed clone. Not a walk. The owner follows
the proposed block verbatim and nothing else, to establish whether it takes
a clean Mac to a working `coga build` unaided.

Pass condition: the five lines complete and `coga build` runs, with no
question asked and no step improvised. Any deviation needed is a defect in
the block, recorded here with the line that failed. Still installing coga
from PyPI, so this verifies the instructions rather than any merged fix.

Predictions on record before the run:

- No Command Line Tools dialog during `uv tool install coga`, because line
  1 installs the compiler first. This is the test of finding 6's fix.
- The agent CLI installer prints no progress while downloading, per
  Anthropic's documentation, so line 4 is a silent wait.
- `claude` requires a paid account at sign-in; the free plan does not
  include Claude Code. If that blocks a new user, it belongs in the
  instructions and is a finding.

### Result — pass, 2026-10-17

The five lines took a clean Mac to a working `coga build` unaided. No
question asked, no step improvised, no deviation. Owner's summary: "It
worked perfectly. Much more smooth. If not for the CLI Developer Tools
download, it would literally take 1 minute."

That number is the case for the change. The walked route took two sessions,
left Coga's documentation twice, hit an unexplained system dialog, and ended
at a dead end requiring an undocumented Node install. The same outcome is
five lines and about a minute of typing, plus Apple's one-time download.

Prediction 1 confirmed: no Command Line Tools dialog during `uv tool install
coga`. Installing the compiler first removes finding 6's mid-install
ambush, so ordering is a real fix rather than a cosmetic one. Finding 7
remains worth fixing on its own terms, since a user with git but no
compiler still meets the 3.15 source build.

Predictions 2 and 3, the silent agent-CLI download and the paid-account
sign-in, were not separately reported and are not claimed as verified.

## New-user walk: Windows — moved out

Deferred 2026-10-18 by owner decision and recreated as
`marketing/fix-installer/test-install-on-windows` (draft). A walk today
would test a path that cannot work, because Coga cannot start on native
Windows at all; it is worth running once the port lands and there is
something to install into. Zach runs it on his own Windows PC, which is
also why it wants its own ticket rather than a section here.

Nothing from the macOS walk is owed to it. The Windows-specific fact this
work produced — that `coga.git` imports `fcntl` at module top, so even
`coga --help` fails — already belongs to
`windows-native/core-port-cli-and-test-suite-pass-on-native-window` and is
listed above among the facts to rehome when `coga/install` is deleted.

## Handoff — implement, 2026-10-18

The macOS walk is complete and the fix is on the branch. Three clean VMs:
one cold walk, one reproduction, one verification of the proposed block.
Sixteen findings, all recorded above with evidence.

What landed in code: one commit, `README.md` only, replacing the install
block with the five-line sequence verified on a clean machine and removing
two false claims — that Coga runs on native Windows, and that `coga init`
offers to install an agent CLI, which the released package does not do.

Three deviations from the owner's dictated text, each raised at the time
and left in deliberately:

- Kept "Linux or macOS" rather than macOS alone, because Coga does run on
  Linux and the owner's wording would have been false in the other
  direction. Line 1 carries a `macOS:` marker so Linux readers skip it.
- Added "Native Windows is unsupported." That fact lives only on the page
  being deleted, and Windows users will try regardless.
- Kept Nico's sentence about uv fetching a compatible Python
  (`ff906aac4`), because the platform line still requires Python 3.11+ and
  nothing in the block installs Python.

Deliberately out of scope, each with a reason recorded above: deleting
`coga/install` (owner is doing it, and the orphan facts need homes first),
capping `requires-python` for finding 7, and teaching the dependency
manifest the agent CLI's native installer for finding 16. The last two need
owner rulings listed under "Decisions needed" in the owner's report.

For the next step: `main` is red independently of this work. Two causes,
both reproduced on the merge-base with this change stashed — a drifted
`coga/recurring/autoclose-merged/ticket.md` twin, and the `CLAUDE.md`
core-boundary text. CI will fail on this PR until someone fixes them, and
that is not this ticket's job.

Also produced, outside the repo: an organised findings report in the
owner's Google Docs, with labelled screenshot slots he fills himself.

## Self-QA — 2026-10-18

Review form: **direct review, completed.** `/code-review` is not an invocable
skill in this harness, so the pass was read by hand over the branch diff vs
`main` — one file, `README.md`. `/simplify` ran, with its four-agent fan-out
replaced by an inline pass over the same four angles, because the diff
contains no code and this session is configured not to spawn subagents
unasked. Recorded as a limitation rather than a clean tool pass. Reviewer is
Claude, the same agent lineage as the implement step: this is self-review,
not independent review.

Findings applied — three, all resolved by one edit (commit `cdf2676b0`):

- **Six command lines against a five-line Done-when.** The implement step's
  block had six commands; the ticket caps the README install at five, and the
  sequence verified on the clean VM was five. `coga build` was that run's
  *pass condition* ("the five lines complete and `coga build` runs"), which
  the implement step folded into the block itself. Removed, owner confirmed.
- **Reuse — that line duplicated `README.md:127`**, which already covers
  `coga build` and correctly conditions it on the repo being empty. The
  install block restated it unconditionally, contradicting "First steps".
- **Existing-project entry point restored.** The old block's
  `cd <your git repository>` served existing repos; the new one hardcodes
  `mkdir myproject && cd myproject && git init`, so a user with a project
  following it literally creates a throwaway directory. Carried in one prose
  sentence after the block rather than a sixth command line.

The five commands are now byte-identical to what passed on the clean VM. The
implement step reworded only the comments, and comments do not execute, so
the verified behavior is preserved exactly.

Claims checked against the code rather than accepted from the diff:

- `pyproject.toml:10` has `requires-python = ">=3.11"`, uncapped — finding 7
  is real and unfixed.
- `src/coga/git.py:49` imports `fcntl` at module top — the new "Native
  Windows is unsupported" sentence is accurate.
- `src/coga/dependencies.py:119-122` gives `claude` only brew and npm —
  findings 14 and 16 are real.
- PyPI's latest is 0.4.0 and `src/coga/agent_cli_setup.py` is absent from
  `v0.4.0`, so dropping the "`coga init` offers to install the agent CLI"
  sentence was right for anyone running `uv tool install coga`.
- Both new installer URLs return HTTP 200, and `https://claude.ai/install.sh`
  is Anthropic's own script, installing under `$HOME` with neither Node nor
  Homebrew — which is what makes line 4 work on a fresh Mac.

No test asserts on the repo README's content, established by reading the
tests rather than assuming: every `test_init.py` reference writes its own
README into a temp target, and `test_edge_distribution.py:47` copies the real
one only because the wheel build needs `pyproject`'s readme, asserting
nothing about its text. A prose edit cannot introduce a failure, and the
suite result below matches the implement step's exactly.

Hand-swept surfaces: none apply. The diff touches no terminal, pager or
Slack surface. The fenced block and line widths were checked as rendered
text.

Not fixed, left for the human reviewer:

- `README.md:110` is 82 characters where the file otherwise wraps at ~78. No
  linter enforces it.
- Line 4 installs Claude Code while the prose above offers Claude *or* Codex;
  five lines has no room for both.
- `README.md:118` still links `docs/contexts/coga/install/SKILL.md`, the page
  the owner is deleting. Not a defect in this diff, but the two changes are
  coupled and that link breaks when the deletion lands.
- The removed agent-CLI sentence is *true on `main`*, so the README now
  understates `main` and will need it back at 0.4.1. This is finding 13's
  unresolved "docs track the release or `main`" question.
- Line 4's `claude` resolves only because line 2's uv installer puts
  `~/.local/bin` on PATH. Fine on the walk, but someone who already had uv
  and skipped line 2's new-terminal step could find `claude` missing.

## PR

```yaml
title: Replace README install block with a verified clean-machine sequence
author: claude
author_evidence: >-
  Both sessions ran as Claude Opus 5 under `coga launch`, attended by the owner
  throughout; no agent override was used. Implement wrote the block
  (`ed321e20e`); self-qa trimmed it to five lines (`cdf2676b0`).
head: cdf2676b0e20f1616ee458c3e496182e8143b91b
base: f6a7145f2cfa8ec3f5602f749d669775ea1be7da
depth: deep
rationale: >-
  Self-qa has completed and its findings are applied, but the depth stays deep
  on three rubric triggers, not on residual doubt about the change itself.
  Review was self-review — the same agent lineage as the implement step, with
  no independent reviewer — the suite is red from five pre-existing main
  failures, and findings 7, 13 and 16 remain open pending owner rulings. The
  change itself is one prose file whose sequence was walked end to end on a
  clean macOS VM, but it is the public front page's install path, the first
  thing every new user executes. An independent review returning green on
  this head is what should downgrade it.
implementation: >-
  Replaces the four-line README install block, which cannot complete on a
  fresh Mac, with the five-line sequence verified on a clean VM; corrects the
  platform sentence; and carries the existing-repository entry point in prose
  after the block.
deviations: >-
  Three departures from the owner's dictated wording, each raised with him
  before committing: kept "Linux or macOS" rather than macOS alone because
  Coga does run on Linux; added "Native Windows is unsupported" because that
  fact's only home is the page being deleted; kept Nico's uv/Python sentence
  from ff906aac4 because the platform line still names Python 3.11+. Self-qa
  then removed the implement step's sixth command, `coga build`, which
  exceeded the ticket's five-line cap and duplicated "First steps"; owner
  confirmed in session.
limitations: >-
  Verified on macOS 26.6.2 arm64 only. The Linux path is reasoned, not walked:
  line 1 is marked macOS-only and Linux users take git from their package
  manager. Line 4 installs the agent CLI with the vendor's own script, which
  sits against the policy in `src/coga/agent_cli_setup.py` that Coga itself
  never runs `curl | sh`; that policy governs what Coga executes, not what the
  README tells a user to run, but the tension is unresolved and is finding 16.
  Two coupled issues are out of scope and recorded under `## Self-QA`: the
  README still links `coga/install`, the page the owner is deleting, so that
  link breaks when the deletion lands; and the removed agent-CLI sentence is
  true on `main`, so the README now understates `main` until 0.4.1.
files:
  README.md: >-
    Install section — the five verified lines, the platform sentence corrected
    to drop the false native-Windows claim and the agent-CLI install offer the
    released package does not have, and a prose sentence for readers who
    already have a repository.
review:
  reviewer: claude(self)
  kind: direct
  status: completed
  detail: >-
    Direct review, completed in the self-qa session — not independent.
    `/code-review` is not an invocable skill in this harness, so the diff was
    read by hand as the step directs for that case; `/simplify` ran as an
    inline pass over its four angles because the diff contains no code. Three
    findings were raised and all three applied in `cdf2676b0`. The diff's
    factual claims were checked against the source rather than accepted:
    `pyproject.toml:10`, `src/coga/git.py:49`, `src/coga/dependencies.py:119`,
    the absence of `agent_cli_setup.py` from `v0.4.0`, and both installer URLs
    returning 200. Full detail under `## Self-QA`.
checks:
  - command: python -m pytest
    status: failed
    head: 69776a5ae (pre-rebase; README byte-identical to cdf2676b0)
    base: 8508d839856fee4623ce03ab2eefbf932d5033e2
    detail: >-
      3776 passed, 5 failed, 8 skipped in 35m44s, run on the working tree after
      the self-qa fix. Recorded at the pre-rebase base deliberately: the rebase
      onto f6a7145f2 moved only coga-state commits and did not touch README.md,
      so the tested README is byte-identical to the committed one, but this
      receipt does not by itself describe the final head — the targeted re-run
      below does.
  - command: python -m pytest (5 known failures + test_compose + test_edge_distribution)
    status: failed
    head: cdf2676b0e20f1616ee458c3e496182e8143b91b
    base: f6a7145f2cfa8ec3f5602f749d669775ea1be7da
    detail: >-
      5 failed, 97 passed in 59s at the final head. The failing set is
      identical to the full run's and to the implement step's: test_packaging
      and test_autoclose_sweep twin drift on
      coga/recurring/autoclose-merged/ticket.md, test_compose's CLAUDE.md
      core-boundary case, test_edge_distribution's legacy-adoption inventory,
      and a test_recurring git update-ref failure. None can be caused by this
      diff: no test asserts on the repo README's content — test_init writes its
      own into a temp target, and test_edge_distribution copies the real one
      only because the wheel build needs pyproject's readme. CI will stay red
      on this PR until main is fixed, which is not this ticket's job.
  - command: coga validate --json
    status: passed
    head: cdf2676b0e20f1616ee458c3e496182e8143b91b
    base: f6a7145f2cfa8ec3f5602f749d669775ea1be7da
    detail: >-
      269 ok, 2 errors, 47 warnings. Both errors are broken-context on
      marketing/demo-hackability-ask-claude-to-add-a-command-live, which this
      work does not touch. This ticket reports only a stuck-in-progress warn.
```

## Blockers

- [x] [2026-10-14 13:19] [agent:claude] id=20261014T131919 Needs an attended session on Zach's own Mac and Windows machines: the ticket is a hands-on clean-install walk (uv tool install coga, coga init, coga build, first ticket) on those machines, which this queued Linux session cannot reach. Relaunch it attended on the Mac, then on Windows. The Windows fcntl port is tracked separately in make-coga-run-on-native-windows.
  resolved: [2026-10-14 16:45] [human:zach] Owner chose rented disposable AWS macOS and Windows hosts; the read-only Mac preflight is green, so the old own-machine attendance premise no longer blocks the ticket.

## Superseded designs

- 2026-10-14: walk on rented AWS hosts (EC2 Mac and EC2 Windows Server).
  Dropped on 2026-10-15 because this ticket is the human counterpart to the
  automated harnesses. No AWS host was allocated and nothing was spent. The
  setup log, cost notes and removal steps now live in Zach's private admin
  repo (ticket `ops/aws-rented-machine-coga-install-testing`), not here.
