---
title: Test and fix install on macOS and Windows
status: blocked
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
- coga/testing/clean-install
agent: claude
---

## Description

Zach (marketing) has a Mac and a Windows machine. Walk a clean install of coga on each, the way a new user would (uv tool install coga, then coga init, coga build, a first ticket), and fix what breaks with the agent in the same session. macOS works but has known first-run problems: the Xcode Command Line Tools git stub, and the system Python 3.9 being below the 3.11 floor. Native Windows does not start at all: src/coga/git.py imports fcntl at module top, so even coga --help fails, and repl_supervisor.py and megalaunch.py also need pty/termios/tty. The deep Windows port is tracked in make-coga-run-on-native-windows (owner decision 2026-10-13: README claims Windows support, so port it). This ticket is the hands-on test-and-fix pass that feeds it. Deliverables: a findings list per OS on the blackboard, fixes as PRs, and docs/contexts/coga/install/SKILL.md updated to match what actually works.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Session 2026-10-14 (megalaunch, Linux host)

- Nothing done yet. This ticket is a hands-on walk on Zach's own Mac and
  Windows machines with an attended agent there. A queued Linux session
  can't reach either machine, and writing per-OS findings without the walk
  would make them up.
- Known items are already tracked elsewhere and were not duplicated here:
  the Windows `fcntl`/pty port is in `make-coga-run-on-native-windows`; the
  Python <3.11 fail-loud is in `marketing/fix-installer/fail-loud-on-python-older-than-3-11`
  (blocked); the CLT stub doc is done (`coga/install` "macOS: install the
  Command Line Tools first").
- Next: run this ticket attended (`coga launch` from a coga checkout on
  Zach's Mac, then on the Windows box) and record findings per OS here.

---

## Blockers

- [ ] [2026-10-14 13:19] [agent:claude] id=20261014T131919 Needs an attended session on Zach's own Mac and Windows machines: the ticket is a hands-on clean-install walk (uv tool install coga, coga init, coga build, first ticket) on those machines, which this queued Linux session cannot reach. Relaunch it attended on the Mac, then on Windows. The Windows fcntl port is tracked separately in make-coga-run-on-native-windows.
