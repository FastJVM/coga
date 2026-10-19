---
title: 'Core port: CLI and test suite pass on native Windows'
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
step: 2 (evaluate-design)
agent: claude
---

## Description

The README, which is the source of truth, says Coga runs on Linux, Windows or
macOS. In fact every command, `coga --help` included, crashes on native
Windows at import time. Owner decision 2026-10-13: the README wins, so port
Coga to native Windows, not WSL.

This is the first of three port tickets. It makes every **non-interactive**
command and the test suite work natively. That includes the deterministic
`ticket.py` phase, `coga run` recipes and the `coga recurring` sweep's
script work. Agent sessions (interactive `coga launch`, `coga chat`,
`coga build`, `coga ticket`'s authoring session, `megalaunch`) belong to
`windows-native/interactive-coga-launch-on-native-windows`. Until that
lands, every surface that would start an agent session must refuse on
Windows with a clear "not supported yet" message, before it changes any
state, and never with a traceback. `windows-native/windows-ec2-test-harness`
is merged (`status: done`). Its `scripts/clean-install/aws-windows.sh`
provides the box, and its `checkout` and `ssh` commands drive the fix loop.

### Fix loop (agent, repeated)

1. Provision a Windows Server 2025 box with the harness, then
   `checkout <branch>`.
2. Over SSH, run `coga --help`, then `python -m pytest`.
3. Fix the failures locally, push, re-checkout, and run again.
4. Run the full Linux suite locally on every iteration, so POSIX behavior
   never changes.
5. Tear the box down at the end of every working session.

The grep and the test survey in `## Context` are a starting map, not a
complete list. The box is the authority: whatever still fails there is in
scope unless it is listed under *Out of scope*.

### Acceptance criteria

- [ ] On a **fresh** Windows Server 2025 instance, after harness `checkout`
      of the branch, `coga --help` exits 0 and the full `python -m pytest`
      passes natively, with no bash on the Administrator's PATH.
- [ ] Every Windows skip uses one shared marker (see *Proposed shape* §7).
      A test of agent-session or PTY behavior may skip with a reason that
      names `windows-native/interactive-coga-launch-on-native-windows`.
      Every other Windows skip is listed in the PR with its reason, and none
      hides a Windows code path that users reach. For example, a test of the
      Windows lock or process-tree path must run on Windows, not skip.
- [ ] On the same box, the harness `walk` installs the **branch** wheel as a
      new local user (not the fix-loop account) and passes every step
      through `coga validate --json`.
- [ ] On Windows, `coga launch <agent-step ticket>`, `coga chat`,
      `coga build`, `coga ticket` (authoring session) and `megalaunch` each
      exit non-zero with one message: agent sessions are not supported on
      native Windows yet, naming the interactive-launch ticket. Ticket
      status, the log and the checkout are unchanged. `coga launch` of a
      ticket whose current step is fully handled by `ticket.py` still runs.
      `coga launch --prompt-report` still works.
- [ ] Coga-written state files (tickets, `log.md`, blackboards, run
      records, config) are LF on Windows, matching POSIX byte for byte.
- [ ] `state_lock` really serializes two processes on Windows. A Windows
      test shows a second process blocks until the first releases the lock.
- [ ] The full Linux suite still passes, with no POSIX test newly skipped
      or weakened.
- [ ] `coga/codebase` (canonical and packaged copies) lists the new module.
      `coga/testing/clean-install/windows-aws` documents the branch-wheel
      walk. The instance is torn down, and `status` confirms nothing is
      left billing.

### Proposed shape

Work in this order. Step 1 alone should get `coga --help` running.

1. **Import-safe POSIX modules.** `src/coga/repl_supervisor.py` imports
   `fcntl`, `pty`, `termios`, `tty` and `select` at module top. About ten
   modules import it only for constants or `emit_done_marker`:
   `commands/{block,bump,mark,slack,owner,common,ticket}.py`,
   `launch.py`, `launch_script.py`, `pr_assist.py`, `megalaunch.py`,
   `recurring_runner.py`, and `tests/conftest.py`. Guard the POSIX imports
   (`if os.name == "posix":` at module top, or import inside the
   PTY-running functions), so importing the module never fails and POSIX
   behavior is unchanged. Do the same for `commands/megalaunch.py`
   (`termios`/`tty`/`select`). Do not port PTY behavior. Also make any
   module-level `signal.SIGWINCH`/`SIGKILL`/`SIGHUP` reference lazy if the
   box shows one.
2. **New core module `src/coga/oscompat.py`.** One interface over the
   platform split, with real consumers on both halves (microkernel rule):
   - `lock_dir(prefix) -> Path`: the per-user lock directory under
     `tempfile.gettempdir()`. On POSIX it keeps today's name,
     `f"{prefix}-{os.getuid()}"`. On Windows the temp dir is already per
     user, so it suffixes a sanitized `getpass.getuser()`. Consumers:
     `git.state_lock()` (`coga-state-publication`) and
     `launch._orientation_checkout_guard()` (`coga-orientation`).
   - `lock_fd(fd, *, blocking: bool)` / `unlock_fd(fd)`: `fcntl.flock`
     `LOCK_EX`/`LOCK_NB`/`LOCK_UN` on POSIX. On Windows,
     `msvcrt.locking(fd, LK_NBLCK, 1)` on byte 0. Blocking mode retries
     that call with a short sleep, because `LK_LOCK` gives up after about
     10 s, and `state_lock` must wait indefinitely. A held lock raises
     `BlockingIOError` in non-blocking mode on both platforms, so
     `_orientation_checkout_guard` keeps its `except BlockingIOError`.
     Consumers: the same two. `git.py` and `launch.py` drop
     `import fcntl`.
   - `ProcessTree`: start a child that owns its whole descendant tree, and
     stop that tree. On POSIX it uses `start_new_session=True`, `os.killpg`
     SIGTERM, then a grace period, then SIGKILL, plus the existing
     "group still exists" probe. On Windows it uses the Job Object, moved
     verbatim from `recurring_clone._WindowsJob` together with its
     `_WINDOWS_JOB_WRAPPER` (Windows has no graceful stop, so "terminate"
     and "kill" are both `TerminateJobObject`). Consumers:
     `recurring_clone._run_clone_script()`/`_stop_clone_script()`, already
     Windows-aware, and `recurring_runner._start_repo_recurring_process()`,
     `_signal_repo_recurring_process_group()`,
     `_repo_recurring_process_group_exists()` and
     `_terminate_repo_recurring_process()`, which today call
     `os.killpg`/`signal.SIGKILL` unguarded. Keep the POSIX sequence and
     its timeouts exactly as they are. Reshape the interface to fit both
     callers, but do not change what either caller observes on POSIX.

   The module holds only these three concerns. It is not a home for future
   one-off platform checks.
3. **`atomicio.atomic_write_text`.** `os.fchmod` does not exist on Windows
   before Python 3.13. Keep it on POSIX. On Windows, skip mode propagation:
   there is no POSIX mode, and `os.chmod` without the write bit would make
   the file read-only and break the next `os.replace`. Open the temp file
   with `newline="\n"`, so text is written LF.
4. **LF-only writes.** Text-mode writes translate `\n` to `\r\n` on Windows,
   and about 38 `write_text(`/`open(..., "w")` sites in `src/coga` and
   `src/coga_edge` write Coga state. Give every site that writes a file
   Coga or Git later reads `newline="\n"`: `Path.write_text(...,
   newline="\n")` on 3.10+, or route it through `atomic_write_text`. This
   keeps the `expect=` byte comparisons in `git.publish()` and
   `write_ticket()` correct, and keeps tickets identical across platforms.
   Reading already normalizes through universal newlines. Check that every
   `read_bytes()` compare also tolerates a CRLF working copy produced by
   `core.autocrlf=true`. `git.py` already notes that a CRLF working copy
   hashes to the LF blob.
5. **Agent-session refusal.** Add one helper in `launch.py`, for example
   `agent_sessions_supported()` plus `_refuse_unsupported_platform(ref)`
   with a single message constant. Call it immediately before each existing
   `_interactive_stdio_has_tty()` agent gate, so it runs before any state
   change:
   - `launch.py`: the `_launch` alignment gate, the main
     `if not _interactive_stdio_has_tty(): _refuse_tty_launch` gate, and
     `_require_agent_after_script`
   - `commands/ticket.py`: the authoring bail and the `pick_agent` gate
   - `commands/megalaunch.py`: the `--pick` gate, and the default sweep
     before it would launch agents
   - `megalaunch.py`'s TTY check
   - `recurring_runner.py`: treat Windows like the no-TTY case, setting
     `agent_spawn_refusal` with a Windows label, so the sweep still runs
     scripts and reports the agent refusal the way it does today.

   As a backstop, make the supervisor's spawn entry (`spawn_agent_session`)
   raise the same clear error on Windows. Do not add a check for each
   command at `cli.py`.
6. **Shells, scripts and paths.** Coga already runs `ticket.py` and clone
   scripts as `[sys.executable, script]` (`launch_script.py`,
   `recurring_clone.py`), so those need no shebang. On the box, check that
   nothing else shells out to `sh`/`bash` or runs an extensionless shebang
   file. `validate._working_tree_carries_mode()` already uses the Git index
   mode off POSIX. Keep it, and check that `dream_validate_drift` and
   `commands/update._chmod_executable` behave sensibly on Windows (a chmod
   that does nothing is fine).
7. **Tests.**
   - `tests/conftest.py`: also point `USERPROFILE` (and `APPDATA`/
     `LOCALAPPDATA` if the box needs it) at the tmp HOME, so `Path.home()`
     is isolated on Windows. Set `core.autocrlf=false` in `init_git_repo`.
     Write fixtures LF.
   - Add one shared marker in `conftest.py`, for example
     `windows_interactive_skip = pytest.mark.skipif(os.name == "nt",
     reason="agent sessions/PTY: windows-native/interactive-coga-launch-on-native-windows")`.
     Apply it to `test_repl_supervisor.py` PTY tests, the pty/SIGWINCH
     tests in `test_megalaunch.py`, and `test_launch_restart.py` if it
     spawns an agent REPL.
   - Fake executables. There is no shared helper today (the survey lists
     the files). Add one `conftest` helper that writes a stub runnable on
     both platforms: a `#!`-script plus chmod on POSIX, and a `.cmd`
     wrapper calling `sys.executable` on Windows. Port `test_open_pr.py`,
     `test_open_pr_command.py`, `test_seed_local_config.py`,
     `test_edge_distribution.py`, `test_init.py` and
     `test_launch_restart.py` to it where the code under test runs on
     Windows.
   - Mode, read-only-directory and exec-bit assertions (`test_validate.py`,
     `test_git.py`, `test_atomicio.py`, `test_seed_local_config.py`,
     `test_publish_state.py`, `test_workspace_discovery.py`) become
     POSIX-only skips, each listed in the PR. Add a Windows-side assertion
     where the Windows behavior differs and matters (atomicio: the write
     succeeds and is LF).
   - `test_clean_install_harness.py` drives bash host scripts. It is a
     host-side harness test and skips on Windows (listed in the PR).
   - Add Windows-run tests for `oscompat` (two-process lock contention,
     non-blocking `BlockingIOError`, ProcessTree kills a grandchild) and
     for the refusal message and its unchanged state.
   - Fix `/`-joined path string comparisons (for example
     `test_service_order.py`) with `Path`/`as_posix`, not skips.
8. **Harness branch-wheel walk.** `aws-windows.sh walk` accepts only
   `pypi|main`, and `main` builds the wheel from `origin/main`. Generalize
   `main` to any fetched ref (keep `main` as the default spelling), so the
   walk can install the branch wheel. Update
   `coga/testing/clean-install/windows-aws` (canonical, plus a packaged
   copy if one exists) and `tests/test_clean_install_harness.py` to match.
9. **Docs.** Add `oscompat.py` to `coga/codebase` (both copies). Note the
   lock behavior on Windows in `coga/sync` only if that topic describes
   `flock`. Do not edit `coga/install`: the interactive ticket owns that.

### Out of scope

- PTY and agent-REPL behavior on Windows: `repl_supervisor`, the
  megalaunch TUI, window-size handling, and the orientation lock's real use
  by `coga chat`. That is the interactive ticket. This ticket only makes
  those modules import and makes the agent path refuse.
- CI (`windows-native/pr-ci-with-linux-and-windows-test-jobs`).
- Updating `coga/install`, the README's platform line, or publishing to
  PyPI.
- macOS changes.
- A general portability layer or a `sys.platform` sweep of code the box
  does not show failing.
- Changing what `coga init` seeds into user repos' `.gitattributes`. That
  is an open question on the blackboard, not part of this design.

## Context

### POSIX-only code (re-grep of `src/` 2026-10-19)

- `cli.py` imports every command module eagerly, so one top-level POSIX
  import anywhere breaks the whole CLI. `cli.py`'s own `SIGPIPE` use is
  already guarded with `hasattr`.
- `repl_supervisor.py`: module-level `fcntl`, `pty`, `select`, `termios`,
  `tty`, plus `os.fork`, `os.killpg` and `SIGWINCH` inside its functions.
  It has importers in about ten modules plus `tests/conftest.py`, which
  means **no test even collects on Windows today**.
- `commands/megalaunch.py`: module-level `termios`/`tty`/`select`, and
  `SIGWINCH` in its picker.
- `git.py`: module-level `import fcntl`. `state_lock()` uses
  `fcntl.flock` (blocking, reentrant per thread through `_HELD_LOCKS`) in
  `tempfile.gettempdir()/coga-state-publication-{os.getuid()}`.
  `write_ticket()` and every `publish` path run under it.
- `launch.py`: module-level `import fcntl`.
  `_orientation_checkout_guard()` takes a **non-blocking** `flock` in
  `coga-orientation-{os.getuid()}`. This is the second consumer that makes
  a shared lock helper legitimate. Its `signal.signal(SIGTERM, …)` exists on
  Windows and is fine.
- `atomicio.py` `atomic_write_text()`: `os.fchmod` plus a text-mode
  `os.fdopen(fd, "w")`, so it writes CRLF on Windows.
- `recurring_runner.py`: `_start_repo_recurring_process()` uses
  `start_new_session=True`. `_signal_repo_recurring_process_group()` and
  `_process_group_is_running()` use `os.killpg`.
  `_terminate_repo_recurring_process()` uses `signal.SIGKILL`, which does
  not exist on Windows. The control relay that runs `coga.cli` in a child
  uses `process.send_signal(SIGTERM)`, which is `TerminateProcess` on
  Windows and acceptable.
- `recurring_clone.py` already has a Windows path: `_WindowsJob`
  (ctypes Job Object with `KILL_ON_JOB_CLOSE`) plus `_WINDOWS_JOB_WRAPPER`,
  and `_run_clone_script()`/`_stop_clone_script()` branch on `os.name`.
  `docs/contexts/coga/recurring/scheduling` documents it. Reuse it; do not
  write a second one.
- `launch_script.py` runs `ticket.py` as `[sys.executable, str(entry),
  *args]`, which needs no shebang.
- `validate.py` `_working_tree_carries_mode()` already returns False off
  POSIX and falls back to Git index modes.
- `commands/init.py` already guards `os.geteuid` and branches on
  `sys.platform == "win32"` for package managers.
- `commands/update.py` `_chmod_executable` uses `0o755`, which is harmless
  on Windows.
- The refusal points for an agent session that exist today are the
  `_interactive_stdio_has_tty()` gates in `launch.py`, `megalaunch.py`,
  `commands/megalaunch.py`, `commands/ticket.py` and `recurring_runner.py`,
  together with `launch._refuse_tty_launch()`.
- `pyproject.toml` has no POSIX-only dependencies. Nothing new is needed:
  `msvcrt` and `ctypes` are stdlib.

### Test-suite survey (2026-10-19, approximate; the box is authoritative)

- There are 79 `test_*.py` files.
- `conftest.py` sets `HOME`/`TMPDIR` but not `USERPROFILE`, and does not
  neutralize `core.autocrlf`.
- PTY or `bash -c` tests: `test_repl_supervisor.py` (about 16),
  `test_megalaunch.py` (pty around the `pty.openpty` test, plus one
  SIGWINCH test), and the process-group section of `test_recurring.py`
  (about 4).
- Fake-executable stubs with no shared helper: `test_open_pr.py` (fake
  `gh`, many tests), `test_open_pr_command.py`, `test_launch_restart.py`,
  `test_seed_local_config.py`, `test_edge_distribution.py`,
  `test_init.py`, and `test_clean_install_harness.py` (bash host
  scripts).
- Mode or read-only assertions: `test_validate.py` (about 8), `test_git.py`,
  `test_atomicio.py`, `test_seed_local_config.py`, `test_publish_state.py`,
  `test_workspace_discovery.py`.
- Golden-byte fixtures (`tests/fixtures/reminders/*`) are at risk under
  CRLF.
- Existing platform skips: `test_recurring_clone.py` (posix/nt pair),
  `test_validate.py`, `test_repl_supervisor.py`, `test_recurring.py`,
  `test_windows_clean_install.py`.

### Design constraints

- POSIX behavior must stay unchanged. Prefer a small platform split behind
  one interface over `sys.platform` checks scattered through the code.
- Platform-marked dependencies (`; sys_platform == "win32"`) are allowed,
  but none are expected.
- **Microkernel boundary** (`coga/extension-model`): a new core helper needs
  two or more real consumers. `oscompat.py` qualifies through three
  concerns, each with two consumers: the lock directory and the lock
  (`git.state_lock`, `launch._orientation_checkout_guard`), and the process
  tree (`recurring_clone`, `recurring_runner`).
- **Shells and scripts.** Coga must run without bash on the PATH. The repo
  `.gitattributes` already forces `*.sh` and `*.ps1` to `eol=lf`.
- Update `coga/codebase` for any new module, editing both the canonical and
  packaged copies (`coga/packaging`). `coga/install` is updated by the
  interactive ticket, once Windows is fully supported.

### AWS

- Use the `coga-test` SSO profile in us-east-1, through the harness runbook
  `coga/testing/clean-install/windows-aws` (sections "Fix loop: checkout
  and remote commands", "Walk" and "Teardown").
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

## Design notes (2026-10-19)

- The spec is under `## Description`. The source re-grep and the test-suite
  survey (a static read; nothing was run on Windows) are under `## Context`.
- Key decisions: (1) one new core module, `oscompat.py`, justified by a
  second consumer for each concern (the orientation lock in `launch.py` was
  missed in the original grep). (2) Refuse at the existing TTY gates, so
  `ticket.py`/script work keeps running on Windows and the refusal happens
  before any state change. (3) Coga writes LF everywhere.
- Harness gap: `walk` takes only `pypi|main`, so acceptance #2 (branch
  wheel) needs a small extension to `aws-windows.sh`.

## Open Questions

1. **Refusal granularity.** Is "refuse at the agent-session gates" right?
   It lets a `ticket.py`-only step launch on Windows. The alternative is
   refusing all `coga launch` on Windows at entry: simpler, but script-mode
   tickets and recurring scripts stay unusable until the interactive
   ticket. Recommend the gates.
2. **User-repo line endings.** Coga will *write* LF. Should `coga init`
   also seed `* text=auto eol=lf` (or `coga/** text eol=lf`) into the
   user repo's `.gitattributes`, so `core.autocrlf=true` checkouts of
   tickets stay LF? The spec defers this as out of scope. Say if it should
   be in.
3. **Lock implementation on Windows.** The spec uses a polling
   `msvcrt.locking` retry for the blocking `state_lock`, which is stdlib
   only. `LockFileEx` through ctypes gives a true kernel wait but adds about
   30 lines of ctypes. Recommend `msvcrt` polling.
4. **Harness change in this ticket.** Is extending `aws-windows.sh walk`
   from `main` to any ref acceptable here, or should it be a follow-up
   ticket to the harness?
