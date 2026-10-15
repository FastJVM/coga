---
title: Test and fix install on macOS and Windows
status: active
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

## Plan (2026-10-14, attended)

Human walk on Zach's own hardware in a fresh VM or fresh user account,
following `guide-for-zach.md`. Steps: pick A/B per OS -> baseline -> walk macOS -> findings and
fixes -> walk Windows -> findings and fixes -> update `coga/install`.

## New-user walk: macOS

(not started)

## New-user walk: Windows

(not started)

## Carried-over finding

- This WSL checkout has 654 tracked files with CRLF in the worktree (index is
  LF; `core.autocrlf=input` hides it from `git status`). `aws-mac.sh` then
  fails `env: 'bash\r': No such file or directory`. Converted only
  `scripts/clean-install/{aws-mac.sh,run.sh,Dockerfile}` back to LF in place.
  Root cause unknown (likely a Windows-side git/editor touched the tree).
  Relevance to Windows users: a repo cloned with Windows git
  `core.autocrlf=true` would CRLF any shell scripts too; check whether coga
  ships/executes `.sh` or `ticket.py` with shebangs on that path.

## Blockers

- [x] [2026-10-14 13:19] [agent:claude] id=20261014T131919 Needs an attended session on Zach's own Mac and Windows machines: the ticket is a hands-on clean-install walk (uv tool install coga, coga init, coga build, first ticket) on those machines, which this queued Linux session cannot reach. Relaunch it attended on the Mac, then on Windows. The Windows fcntl port is tracked separately in make-coga-run-on-native-windows.
  resolved: [2026-10-14 16:45] [human:zach] Owner chose rented disposable AWS macOS and Windows hosts; the read-only Mac preflight is green, so the old own-machine attendance premise no longer blocks the ticket.

## Superseded designs

- 2026-10-14: walk on rented AWS hosts (EC2 Mac and EC2 Windows Server).
  Dropped on 2026-10-15 because this ticket is the human counterpart to the
  automated harnesses. No AWS host was allocated and nothing was spent. The
  setup log, cost notes and removal steps now live in Zach's private admin
  repo (ticket `ops/aws-rented-machine-coga-install-testing`), not here.
