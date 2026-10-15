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
   step through `coga validate --json`. The walk runs as a new local user,
   separate from the fix-loop account.
3. **The agent itself runs an attended `coga launch`** on the box with
   Claude Code, primarily over `ssh -t` (Windows OpenSSH gives the session a
   ConPTY). Whether Claude Code's TUI behaves there is something the design
   step must check early. If it doesn't, the fallback is the owner running
   the same check over RDP. The REPL
   starts, the agent's `coga bump` ends the session, and the supervisor tears
   the child down cleanly with no orphaned processes. A `coga mark done`
   path works the same way.
4. A `windows-latest` GitHub Actions job runs the pytest suite on every PR,
   so Windows can't silently break again. The interactive launch stays an
   EC2-only check. There is no PR CI today (`.github/workflows/` holds only
   `release.yml`), so this means creating a new PR workflow. Run it on
   `ubuntu-latest` as well.
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
  lock (for example `msvcrt.locking`), not only an import guard.
- `atomicio.py`: `os.fchmod`, which doesn't exist on Windows before Python
  3.13. Every atomic write goes through it, so once the imports are fixed,
  every state write would fail on 3.11.
- `commands/update.py`: `_chmod_executable` sets `0o755` on packaged
  scripts. On Windows this is harmless but meaningless; decide whether to
  skip it.
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
  shared infrastructure with two or more real consumers
  (`coga/extension-model`). The supervisor takes no lock; it only uses
  `fcntl.ioctl` for the window size. So unless the design finds a second
  real consumer, the portable lock stays inside `git.py`. Don't grow new
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

## Evaluator review

Cold review of both `windows-native/` tickets (2026-10-14). Already folded into
the bodies: the uv install order, the fix-loop user, RDP confirmed by the owner,
`atomicio.fchmod`, `update.py` chmod, no second lock consumer, PR CI created from
scratch, a separate walk user, and SSH+ConPTY as the primary launch path. Still
open, for the owner to decide: split the port further; a step of its own for
Zach's walk; a standing spend approval; encoding the dependency (Coga has no
`depends_on` field, so it is prose only).

- Harness HIGH: paid live run plus RDP check inside the agent implement step; uv
  `UV_PYTHON_DOWNLOADS=never` ordering ambiguous.
- Harness MED: no user/uv named for `checkout`; code/implement layer is 48% of
  prompt (bundled skill, not trimmable here).
- Port HIGH: scope too big — suggests split into (1) core port + suite green,
  (2) interactive supervisor + attended launch, (3) windows CI (no PR CI exists
  today), (4) docs + Zach walk. Fix loop with paid EC2 is one implement step;
  Zach's walk has no step of its own. Agent can't drive RDP.
- Port MED: `atomicio.py` `os.fchmod` missing on Windows <3.13 (every write
  path); `update.py` chmod; lock-helper "two consumers" claim false (supervisor
  only uses `fcntl.ioctl`).
- Port note: consider attaching `coga/launch` to the design step for the
  teardown contract.
- Cross: decide once whether the agent may provision after first approval;
  encode the dependency; walk-vs-fix-loop on same box must not collide.
- Verified accurate: README:88, install SKILL Windows text, git.py fcntl/getuid,
  supervisor pty/fork/killpg/TIOCSWINSZ, megalaunch termios, recurring_runner
  start_new_session/killpg, init geteuid guard, provenance refs in log.
