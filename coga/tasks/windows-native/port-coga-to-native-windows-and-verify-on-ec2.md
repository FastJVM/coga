---
title: Port coga to native Windows and verify on EC2
status: draft
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
---

## Description

The README, which is the source of truth, says Coga runs on Linux, Windows or
macOS. In fact every command, `coga --help` included, crashes on native
Windows at import time. `docs/contexts/coga/install/SKILL.md` documents
Windows as unsupported and WSL as untested. Owner decision 2026-10-13: the
README wins. Port Coga to native Windows (not WSL) with full interactive
`coga launch`. Prove it in a fix loop on a real Windows EC2 machine, then
make `coga/install` match the README.

Start after `windows-native/windows-ec2-test-harness` is merged. It provides
`scripts/clean-install/aws-windows.sh` and its runbook. Use its `checkout`
and `ssh` commands for the loop below.

### Fix loop (agent, repeated)

1. Provision a Windows Server 2025 box with the harness, then
   `checkout <branch>`.
2. Over SSH, run `coga --help`, then `python -m pytest`.
3. Fix the failures locally, push, re-checkout, and run again.
4. Run the full Linux suite locally on every iteration, so the port never
   regresses POSIX.
5. Tear the box down at the end of each working session. Don't leave it
   running overnight.

### Acceptance (done when all hold)

1. On a **fresh** instance, the full `python -m pytest` suite passes
   natively. Each test skipped as POSIX-only is listed in the PR with its
   reason. A skip must not hide a Windows code path that users reach.
2. On the same box, the harness `walk` with the branch wheel passes every
   step through `coga validate --json`.
3. **The agent itself runs an attended `coga launch`** on the box with
   Claude Code, in a real console over RDP or SSH with ConPTY. The REPL
   starts, the agent's `coga bump` ends the session, and the supervisor tears
   the child down cleanly with no orphaned processes. A `coga mark done`
   path works the same way.
4. A `windows-latest` GitHub Actions job runs the pytest suite on every PR,
   so Windows can't silently break again. The interactive launch stays an
   EC2-only check.
5. The Linux suite still passes, and the instance is torn down.
6. `docs/contexts/coga/install/SKILL.md` and its packaged twin list native
   Windows as supported. They add a Windows baseline: Python 3.11+ through
   uv, PATH after `uv tool install`, Git for Windows and line endings,
   PowerShell as the shell, and agent CLI support. README line 88 stays
   true.
7. **Final human check:** after the PR is open and before merge, Zach
   installs the PR's wheel on Windows by following
   `marketing/fix-installer/test-and-fix-install-on-macos-and-windows`'s
   guide. He walks install, then `coga init`, then a first `coga ticket`.
   The `review` step tracks his findings, and blocking ones are fixed before
   merge.

## Context

### POSIX-only code to port (grep of `src/`, 2026-10-14; re-grep at design)

- `git.py`: `import fcntl` at module top. `fcntl.flock` takes the
  state-publication lock, and the lock directory name uses `os.getuid()`.
  Both run for ordinary commands, not just launch, so this needs a portable
  lock (for example `msvcrt.locking`, or a small shared lock helper), not
  only an import guard.
- `repl_supervisor.py`: `pty`, `fork`, `termios`, `tty`, `select`, `fcntl`
  (a `TIOCSWINSZ` window-size ioctl), `killpg`, SIGTERM→SIGKILL escalation,
  and a SIGINT/SIGTERM masking window. This is the supervisor that runs the
  agent REPL and tears it down when the done signal arrives. It is the heart
  of the port.
- `commands/megalaunch.py`: top-level `termios`/`tty`/`select` for its
  picker.
- `recurring_runner.py`: `Popen(start_new_session=True)` plus
  `os.killpg` to stop the child's process group.
- `commands/init.py`: already guards `os.geteuid` with `hasattr`.
- `cli.py` imports every command module eagerly, so one top-level POSIX
  import anywhere breaks the whole CLI.

### Decisions for the design step

- **Supervisor.** Options: ConPTY through a new dependency such as
  `pywinpty` (behaves like the POSIX path; adds a Windows-only wheel
  dependency), or a subprocess without a PTY (no dependency, but the agent
  TUIs may misbehave without a TTY). Choose with evidence from the box, and
  keep the POSIX path byte-for-byte unchanged in behavior. A platform split
  behind one small interface is preferable to sprinkled `sys.platform`
  checks.
- **Termination on Windows.** There are no process groups or POSIX
  signals. Use `CREATE_NEW_PROCESS_GROUP` with `CTRL_BREAK_EVENT`, a Job
  Object, or `taskkill /T /F`, and decide how the SIGTERM grace period
  translates.
- **Dependencies.** Platform-marked dependencies
  (`; sys_platform == "win32"`) are allowed. Changes to `pyproject.toml`
  flow into the wheel, which `coga/packaging` covers.
- **Shells and scripts.** Coga must run on Windows without bash on the
  path. Check any place it shells out to `sh`/`bash`, executes shebang
  scripts (`ticket.py`, skill scripts) or assumes `/` paths, and check
  CRLF handling when Git for Windows uses `core.autocrlf=true`.
- **Microkernel boundary.** Platform helpers go in core only if they are
  shared infrastructure (`coga/extension-model`). The lock helper qualifies
  because both `git.py` and the supervisor need it. Don't grow new
  machinery for the sake of it.

### Topics to update in the same PR

- `coga/install`, plus `coga/launch` if supervisor behavior or its
  documented POSIX assumptions change. `coga/codebase` gets the new module
  map. Edit both the canonical and packaged copies; `coga/packaging` has the
  twin rule.

### Provenance

- This ticket replaces `make-coga-run-on-native-windows`; grep `coga/log.md`
  for that ref.
- It also absorbs the parked draft `_v2/fix-windows-cli-import-crash`. That
  draft's tier-1 import guard is subsumed by full support. Its WSL-only
  option was rejected by the 2026-10-13 decision.
- The installer ticket
  `marketing/fix-installer/test-and-fix-install-on-macos-and-windows`
  hands its Windows findings to this ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
