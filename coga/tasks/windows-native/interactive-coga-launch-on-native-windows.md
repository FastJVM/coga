---
title: Interactive coga launch on native Windows
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
agent: claude
---

## Description

Make interactive `coga launch` (and `coga megalaunch`'s picker) work on
native Windows, then declare Windows supported. This is the last of the
three port tickets. Start after
`windows-native/core-port-cli-and-test-suite-pass-on-native-window` is
merged. That ticket leaves launch on Windows failing with a clear
unsupported message; this ticket replaces that message with a working
supervisor.

Use the same fix loop as the core ticket: harness box, `checkout`, run over
SSH, fix, repeat. Run the Linux suite on every iteration, and tear the box
down at the end of each session.

### Acceptance (done when all hold)

1. **The agent itself runs an attended `coga launch`** with Claude Code on a
   fresh box, primarily over `ssh -t` (Windows OpenSSH gives the session a
   ConPTY).
   - The REPL starts.
   - The agent's `coga bump` ends the session.
   - The supervisor tears the child down cleanly, leaving no orphaned
     processes.
   - `coga mark done` and `coga block` end it the same way.

   If Claude Code's TUI doesn't work over SSH, the fallback is the owner
   running the same check over RDP. Check this early in the design step.
2. The Windows-skipped launch tests from the core ticket are re-enabled, or
   replaced with Windows equivalents, and the full suite passes on Windows
   and Linux.
3. `docs/contexts/coga/install/SKILL.md` and its packaged twin list native
   Windows as supported. They add a Windows baseline: Python 3.11+ through
   uv, PATH after `uv tool install`, Git for Windows and line endings,
   PowerShell as the shell, and agent CLI support. `coga/launch` documents
   the Windows supervisor if its contract changes. README line 88 stays
   true.
4. **Final human check:** after the PR is open and before merge, Zach
   installs the PR's wheel on his own Windows machine by following
   `marketing/fix-installer/test-and-fix-install-on-macos-and-windows`'s
   guide. He walks install, then `coga init`, then a first `coga ticket`.
   The owner's `review` step tracks his findings, and blocking ones are
   fixed before merge.

## Context

### What has to be ported

- `repl_supervisor.py` runs the agent REPL. It uses `pty`, `os.fork`,
  `termios`, `tty`, `select`, `fcntl.ioctl(TIOCSWINSZ)`, `os.killpg`, a
  SIGTERM-then-SIGKILL grace escalation, and a SIGINT/SIGTERM masking window
  around done-signal delivery.
- `commands/megalaunch.py` uses `termios`/`tty`/`select` for its keyboard
  picker. `msvcrt` is the Windows counterpart.

### Decisions for the design step

- **PTY.** Options:
  - ConPTY through a platform-marked dependency such as `pywinpty`. This
    behaves like the POSIX path but adds a Windows-only wheel dependency.
  - A plain subprocess with no PTY. No dependency, but agent TUIs may
    misbehave without a TTY.

  Choose with evidence from the box.
- **Termination.** Windows has no process groups or POSIX signals. Use a Job
  Object (kill-on-close), or `CREATE_NEW_PROCESS_GROUP` with
  `CTRL_BREAK_EVENT`, and decide how the grace period translates. Reuse
  whatever the core ticket built for `recurring_runner`, if it fits.
- POSIX behavior must stay unchanged. Put the platform split behind one
  small interface.
- Read `coga/launch` (`docs/contexts/coga/launch/SKILL.md`): its supervisor
  and teardown sections are the contract the Windows path must honor.

### AWS

The same rules as the core ticket apply: the `coga-test` profile, the
`coga/testing/clean-install/windows-aws` runbook, and the 2026-10-14
standing approval to provision and tear down after the owner's first OK,
with teardown at the end of every session.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
