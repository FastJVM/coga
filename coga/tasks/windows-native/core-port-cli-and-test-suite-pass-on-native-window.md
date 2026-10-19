---
title: 'Core port: CLI and test suite pass on native Windows'
status: active
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

The README, which is the source of truth, says Coga runs on Linux, Windows or
macOS. In fact every command, `coga --help` included, crashes on native
Windows at import time. Owner decision 2026-10-13: the README wins, so port
Coga to native Windows, not WSL.

This is the first of three port tickets. It makes every **non-interactive**
command and the test suite work natively. Interactive `coga launch` belongs
to `windows-native/interactive-coga-launch-on-native-windows`; until that
lands, launch on Windows must fail with a clear "not supported yet" error,
never a traceback. Start only after `windows-native/windows-ec2-test-harness`
is merged. Its `aws-windows.sh` provides the box, and its `checkout` and
`ssh` commands drive the fix loop.

### Fix loop (agent, repeated)

1. Provision a Windows Server 2025 box with the harness, then
   `checkout <branch>`.
2. Over SSH, run `coga --help`, then `python -m pytest`.
3. Fix the failures locally, push, re-checkout, and run again.
4. Run the full Linux suite locally on every iteration, so POSIX behavior
   never changes.
5. Tear the box down at the end of every working session.

### Acceptance (done when all hold)

1. On a **fresh** instance, `coga --help` and the full `python -m pytest`
   suite pass natively.
   - Tests of interactive launch may be skipped on Windows, with a skip
     reason that names the interactive-launch ticket.
   - Every other skip is listed in the PR with its reason.
   - A skip must not hide a Windows code path that users reach.
2. On the same box, the harness `walk` with the branch wheel passes every
   step through `coga validate --json`. It runs as a new local user,
   separate from the fix-loop account.
3. `coga launch` on Windows exits with a clear unsupported-for-now message.
4. The Linux suite still passes, and the instance is torn down.

## Context

### POSIX-only code (grep of `src/` 2026-10-14; re-grep at design)

- `cli.py` imports every command module eagerly, so one top-level POSIX
  import anywhere breaks the whole CLI. In particular,
  `cli` → `commands/block.py` → `repl_supervisor` pulls in
  `fcntl`/`pty`/`termios`/`tty`/`select`, and `commands/megalaunch.py`
  imports `termios`/`tty`/`select` at the top. In this ticket they only need
  to *import* safely. Porting them is the interactive ticket's job.
- `git.py`: `import fcntl` at module top. `fcntl.flock` takes the
  state-publication lock, and the lock directory name uses `os.getuid()`.
  Both run on ordinary commands, so this needs a real portable lock (for
  example `msvcrt.locking`), not just a guard.
- `atomicio.py`: `os.fchmod` doesn't exist on Windows before Python 3.13.
  Every atomic write goes through it.
- `recurring_runner.py`: `Popen(start_new_session=True)` plus `os.killpg` to
  stop the child's process group. On Windows, use
  `CREATE_NEW_PROCESS_GROUP` with `CTRL_BREAK_EVENT`, a Job Object, or
  `taskkill /T`.
- `commands/update.py`: `_chmod_executable` sets `0o755`. On Windows this is
  harmless but meaningless.
- `commands/init.py` already guards `os.geteuid` with `hasattr`.

### Design constraints

- POSIX behavior must stay unchanged. Prefer a small platform split behind
  one interface over `sys.platform` checks scattered through the code.
- Platform-marked dependencies (`; sys_platform == "win32"`) are allowed.
- **Microkernel boundary** (`coga/extension-model`): a new core helper needs
  two or more real consumers. The supervisor takes no lock (it only uses
  `fcntl.ioctl` for the window size), so the portable lock stays inside
  `git.py` unless the design finds a second consumer.
- **Shells and scripts.** Coga must run without bash on the PATH. Check
  where it shells out to `sh`/`bash`, runs shebang scripts (`ticket.py`,
  skill scripts) or assumes `/` paths, and check CRLF when Git for Windows
  uses `core.autocrlf=true`.
- Update `coga/codebase` for any new module, editing both the canonical and
  packaged copies (`coga/packaging`). `coga/install` is updated by the
  interactive ticket, once Windows is fully supported.

### AWS

- Use the `coga-test` SSO profile in us-east-1, through the harness runbook
  `coga/testing/clean-install/windows-aws`.
- Owner decision 2026-10-14: after the owner approves the first provision,
  the agent may provision and tear down Windows instances itself, as long as
  it tears down at the end of every session.
- Never write account IDs or credentials into tickets or PRs.

### Provenance

- This ticket replaces `make-coga-run-on-native-windows` (grep
  `coga/log.md`).
- It absorbs the parked draft `_v2/fix-windows-cli-import-crash`. Its WSL
  option was rejected on 2026-10-13.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
