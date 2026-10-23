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
step: 5 (open-pr)
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
`windows-native/03-interactive-coga-launch-on-native-windows`. Until that
lands, every surface that would start an agent session must refuse on
Windows with a clear "not supported yet" message, before it changes any
state, and never with a traceback. The Windows AWS clean-install harness is
merged; its runbook is the `coga/testing/clean-install/windows-aws` skill
(`coga/skills/coga/testing/clean-install/windows-aws/SKILL.md`). Its
`scripts/clean-install/aws-windows.sh` provides the box, and its `checkout`
and `ssh` commands drive the fix loop.

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

- [x] On a **fresh** Windows Server 2025 instance, after harness `checkout`
      of the branch, `coga --help` exits 0 and the full `python -m pytest`
      passes natively, with no bash on the Administrator's PATH.
- [x] Every Windows skip uses one shared marker (see *Proposed shape* §7).
      A test of agent-session or PTY behavior may skip with a reason that
      names `windows-native/03-interactive-coga-launch-on-native-windows`.
      Every other Windows skip is listed in the PR with its reason, and none
      hides a Windows code path that users reach. For example, a test of the
      Windows lock or process-tree path must run on Windows, not skip.
- [x] On the same box, the harness `walk` installs the **branch** wheel as a
      new local user (not the fix-loop account) and passes every step
      through `coga validate --json`.
- [x] On Windows, `coga launch <agent-step ticket>`, `coga chat`,
      `coga build`, `coga ticket` (authoring session) and `megalaunch` each
      exit non-zero with one message: agent sessions are not supported on
      native Windows yet, naming the interactive-launch ticket. Ticket
      status, the log and the checkout are unchanged. `coga launch` of a
      ticket whose current step is fully handled by `ticket.py` still runs.
      `coga launch --prompt-report` still works.
- [x] Coga-written state files (tickets, `log.md`, blackboards, run
      records, config) are LF on Windows, matching POSIX byte for byte.
- [x] `state_lock` really serializes two processes on Windows. A Windows
      test shows a second process blocks until the first releases the lock.
- [x] The full Linux suite still passes, with no POSIX test newly skipped
      or weakened.
- [x] The local-only `coga-dev/codebase` lists the new module.
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
     reason="agent sessions/PTY: windows-native/03-interactive-coga-launch-on-native-windows")`.
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
9. **Docs.** Add `oscompat.py` to the local-only `coga-dev/codebase`. Note the
   lock behavior on Windows in `coga/sync` only if that topic describes
   `flock`. Do not edit `coga/install`: the interactive ticket owns that.

### Out of scope

- PTY and agent-REPL behavior on Windows: `repl_supervisor`, the
  megalaunch TUI, window-size handling, and the orientation lock's real use
  by `coga chat`. That is the interactive ticket. This ticket only makes
  those modules import and makes the agent path refuse.
- CI (`windows-native/02-pr-ci-with-linux-and-windows-test-jobs`).
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
- **Microkernel boundary** (`coga-dev/microkernel`): a new core helper needs
  two or more real consumers. `oscompat.py` qualifies through three
  concerns, each with two consumers: the lock directory and the lock
  (`git.state_lock`, `launch._orientation_checkout_guard`), and the process
  tree (`recurring_clone`, `recurring_runner`).
- **Shells and scripts.** Coga must run without bash on the PATH. The repo
  `.gitattributes` already forces `*.sh` and `*.ps1` to `eol=lf`.
- Update the local-only `coga-dev/codebase` for any new module
  (`coga-dev/packaging`). `coga/install` is updated by the
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

## Dev

pr: https://github.com/FastJVM/coga/pull/1093
branch: coga/windows-native-01-core-port-cli-and-test-suite-p-2e174f

## Implement handoff — 2026-10-23

Implementation complete, committed and pushed; ready for the workflow handoff.
No PR opened or code review performed in this step.

Approved evaluator corrections and native fixes are detailed under PR. Hybrid
scripts retain work and exit 2; recurring periods pause. The owner approved
restoring the generated principles copy with existing tests. User-repo
.gitattributes and interactive support remain out of scope.

Full Windows: 3953 passed, 102 skips; Linux: 4045 passed, 10 Windows-only skips.
The final state-only rebase preserved runtime/tests/package inputs; fresh Linux,
26 native checks, help and fixture validation passed. Portwalk6 passed all 16
fresh-user branch-wheel steps. PR receipts retain exact tested OIDs and list
all 62 non-interactive exclusions; native locks/Job Objects/recovery run.

AWS teardown/status verified at 2026-10-23 17:11:40 UTC: terminated, no volumes,
security group or key remaining. Temporary tasks/processes and all three
Defender exclusions were removed first. Resource/environment details are in PR.
Receipts: .coga/clean-install/win-core-20261022/ and /tmp/coga-windows-*18*.
Earlier failed/interrupted attempts are retained in Superseded designs.

Follow-up for review/retro: commands/uninstall.py::_uninstall_via_tool prints
POSIX VAR=value syntax in Windows recovery hints; execution is correct. No
existing ticket found. Preserve this finding until its durable owner receives it.

## Open-PR handoff — 2026-10-23

Filed the uninstall-hint follow-up as draft
`windows-native/uninstall-recovery-hints-use-posix-env-syntax-on-w` (open-pr
obligation check). The workflow has no code-review step before open-pr; no code
review was performed. The owner `review` step remains.

## PR

```yaml
title: Port non-interactive Coga to native Windows
author: codex
author_evidence: 'Actual implementing session: Codex (GPT-6 per session instructions), with no model override
  or subagents.'
head: 777c6bab056668afe6305f2c371f58aa7a44eabe
base: d3b8e886ea293cc373f8f4be14061b2bc4738ebd
depth: deep
rationale: Significant native state-publication, locking, process ownership and launch-admission changes
  warrant close review. No code review has run.
implementation: Makes the CLI import on Windows and runs deterministic ticket scripts, recipes and recurring
  work natively. Shared oscompat helpers provide per-user locks, indefinite Windows lock waits and owned
  process trees. Named Job Objects and non-destructive ownership probes preserve conservative crash recovery
  and transcripts. State/template text uses UTF-8 and owned files use LF; Git paths, index modes, context
  links and command wrappers work natively. Agent entry refuses before checkout, publication or draft
  creation and suppresses the exit sweep; prompt reports and script-only work remain available. The harness
  can install an exact fetched branch wheel as a fresh Windows user.
deviations: 'Applied the approved evaluator corrections: refusal precedes the existing TTY gates, hybrid
  scripts retain completed work and exit nonzero (recurring periods pause), ownership proof survives supervisor
  death, and UTF-8 reads accompany LF writes. Native failures also required Git index/path handling, portable
  executable/serialized-path fixtures and the base interpreter for the stdlib Job Object wrapper, so a
  Windows venv launcher cannot end descendant ownership early. Canonicalized test fixture path spelling
  for Windows logon variants without changing assertions. Reconciled newer main topics and restored the
  generated principles copy at the owner’s explicit direction, keeping its tests.'
limitations: |
  Interactive sessions remain unsupported pending windows-native/03-interactive-coga-launch-on-native-windows (40 skipped cases).
  All Windows exclusions use tests/conftest.py::windows_skip(reason). The other 62 skipped cases are enumerated below; native lock and Job Object tests run.
  - tests/test_atomicio.py::test_atomic_write_preserves_existing_mode: POSIX permission modes and umask.
  - tests/test_atomicio.py::test_atomic_write_uses_umask_mode_for_new_file: POSIX permission modes and umask.
  - tests/test_authoring.py::test_finalize_authored_publishes_a_mode_only_change: POSIX filesystem mode bits and permissions.
  - tests/test_clean_install_harness.py::test_windows_walk_builds_the_fetched_ref; variants [main], [feature/windows-port]: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_reaches_init_from_selected_artifact; variants [pypi], [wheel]: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_preserves_failure_and_stops; variants [install], [--version], [init], [validate]: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_refuses_unpinned_python; variants [unpinned0], [unpinned1]: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_refuses_other_python_before_install: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_refuses_reuse: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_ticket_keeps_terminal_stdio: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_build_records_onboarding_outcome: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_build_records_failure_and_removed_ticket: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_build_needs_init: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_main_builds_fetched_commit_not_working_tree: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_aws_mac_provision_needs_cost_approval: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_aws_mac_records_every_resource_and_tears_down: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_aws_mac_stops_on_failed_resource_capture; variants [get-caller-identity-CALLER-create-key-pair], [create-security-group-SG_ID-allocate-hosts], [allocate-hosts-HOST_ID-run-instances], [run-instances-INSTANCE_ID-wait]: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_aws_mac_passwords_stay_out_of_logs: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_aws_mac_walk_quotes_remote_argv: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_aws_mac_main_walk_without_gnu_checksum: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_macos_walk_provisions_and_pins_python_311: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_can_pin_a_pypi_release: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_release_check_does_not_claim_success_after_failure; variants [launch], [incomplete], [log], [dirty], [validate]: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_release_check_requires_successful_init: Unix host-side bash clean-install harness.
  - tests/test_clean_install_harness.py::test_clean_install_host_applies_release_pin_only_to_pypi; variants [pypi], [main]: Unix host-side bash clean-install harness.
  - tests/test_edge_distribution.py::test_documented_interpreter_uses_console_script_shebang; variants [user], [tool-link]: POSIX shell migration runbook; native installed-wheel behavior is tested separately.
  - tests/test_edge_distribution.py::test_documented_interpreter_refuses_unknown_launcher; variants [#!/bin/sh], [#!/usr/bin/env python3], [#!/missing/python3]: POSIX shell migration runbook; native installed-wheel behavior is tested separately.
  - tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers: POSIX shell migration runbook; native installed-wheel behavior is tested separately.
  - tests/test_git.py::test_unwritable_object_dir_names_checkout_destination_and_cause: POSIX directory write permissions.
  - tests/test_git.py::test_prepare_refuses_a_mode_change_with_equal_bytes: POSIX filesystem mode bits and permissions.
  - tests/test_publish_state.py::test_publish_state_recovers_a_bump_whose_object_writes_were_denied: POSIX filesystem mode bits and permissions.
  - tests/test_recurring.py::test_control_worktree_reaps_cancelled_child_before_removal: POSIX process groups and graceful signals; native Windows Job Object tests cover termination.
  - tests/test_recurring.py::test_control_worktree_child_starts_in_an_isolated_session: POSIX process groups and graceful signals; native Windows Job Object tests cover termination.
  - tests/test_recurring.py::test_control_relay_waits_for_real_child_shutdown; variants [pid-sigterm], [terminal-sigint]: POSIX process groups and graceful signals; native Windows Job Object tests cover termination.
  - tests/test_recurring.py::test_recurring_relay_forwards_sigterm_and_waits_for_child: POSIX signal forwarding.
  - tests/test_recurring_clone.py::test_clone_timeout_kills_descendant_holding_stdout; variants [True], [False]: POSIX process-group cleanup.
  - tests/test_seed_local_config.py::test_seed_permission_failure_is_fatal: POSIX local-config permission restriction.
  - tests/test_validate.py::test_validate_reports_non_executable_shebang_skill_script: POSIX filesystem mode bits and permissions.
  - tests/test_validate.py::test_validate_ignores_global_filemode_outside_git: requires trustworthy POSIX modes.
  - tests/test_validate.py::test_validate_checks_bundled_shebang_scripts: POSIX filesystem mode bits and permissions.
  - tests/test_windows_clean_install.py::test_windows_ssh_transports_literal_arguments_and_exit_code: The AWS driver runs on a Unix host.
  - tests/test_workspace_discovery.py::test_strict_mode_raises_on_an_unreadable_directory: POSIX filesystem mode bits and permissions.

  Adjacent follow-up: commands/uninstall.py::_uninstall_via_tool still prints POSIX VAR=value syntax in manual recovery hints on Windows; its actual subprocess receives the correct environment. No existing follow-up ticket was found. The implement handoff retains this finding for the later review/retro step.
files:
  .gitattributes: Keep this repository’s .gitignore LF under Git for Windows.
  .gitignore: Remove blank ignore lines that become CR-only patterns in a CRLF checkout.
  coga/context.md: Restore the generated principles copy after the owner resolved conflicting main state-sync
    intent; retain existing composition tests.
  coga/skills/code/implement/seed_local_config.py: Seed native Windows clones without POSIX permission
    assumptions and recognize the venv launcher.
  coga/skills/coga/testing/clean-install/windows-aws/SKILL.md: Document branch-wheel walks and their separate
    fresh-user evidence.
  docs/contexts/coga-dev/codebase/SKILL.md: Register oscompat and its shared lock/process consumers in
    the local source map.
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: Specify Windows byte-range locking and indefinite
    blocking retries.
  docs/contexts/coga-dev/internals/recurring-clone/SKILL.md: Name shared ProcessTree ownership and native
    descendant deadlines.
  docs/contexts/coga-dev/internals/recurring-temp-worktrees/SKILL.md: Specify named Job Object identities,
    non-destructive probes and conservative crash recovery.
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Document native text encoding and index-based
    executable-mode fingerprints.
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: Document native directory/submodule
    publication rejection.
  docs/contexts/coga-dev/testing/SKILL.md: Document canonical native fixture paths, shared exclusions
    and installed test tools.
  docs/contexts/coga/checkouts/launch-boundary/SKILL.md: Document Windows agent refusal before checkout
    or state changes.
  docs/contexts/coga/checkouts/sandbox-clone/SKILL.md: Document Windows local-config seeding and launcher
    behavior.
  docs/contexts/coga/cli/SKILL.md: Document UTF-8 CLI streams on native Windows.
  docs/contexts/coga/context-layout/SKILL.md: Document Windows index symlink rejection when Git materializes
    links as regular files.
  docs/contexts/coga/launch/SKILL.md: Define early Windows agent refusal, prompt-report and script exceptions,
    and retained hybrid work.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Define Windows script execution and existing pause
    policy after agent refusal.
  docs/contexts/coga/script-tickets/SKILL.md: Specify Windows deterministic scripts, UTF-8 streams and
    retained hybrid work.
  docs/contexts/coga/state-publication/SKILL.md: Specify UTF-8/LF state and exact CAS behavior with Git
    clean filters.
  docs/contexts/coga/tickets/authoring/SKILL.md: Document agent refusal before authoring creates a draft.
  docs/contexts/coga/tickets/discovery/SKILL.md: Specify slash-qualified task refs and audit tags on every
    native platform.
  docs/contexts/coga/workflows/SKILL.md: Preserve invalid local-override errors under Windows ENOENT behavior.
  pyproject.toml: Install pip in the test extra for installed-wheel tests in uv environments.
  scripts/clean-install/aws-windows.sh: Build a walk wheel from an arbitrary fetched ref and record its
    immutable source commit.
  src/coga/atomicio.py: Write UTF-8/LF atomically and keep POSIX mode propagation off Windows.
  src/coga/authoring.py: Fingerprint Windows executable modes from the Git index.
  src/coga/autoclose.py: Use UTF-8 reads and LF state writes.
  src/coga/branchcleanup.py: Use UTF-8 reads and LF state writes.
  src/coga/branchsweep.py: Use UTF-8 reads and LF state writes.
  src/coga/checkouts.py: Use shared native lock paths and locks, and Git index modes in Windows checkout
    proofs.
  src/coga/cli.py: Use UTF-8 CLI streams on Windows without forcing Python UTF-8 file mode.
  src/coga/commands/init.py: Use UTF-8 reads and LF state writes.
  src/coga/commands/megalaunch.py: Guard POSIX imports and refuse Windows agent selection/sweeps before
    mutation.
  src/coga/commands/ticket.py: Refuse Windows authoring before draft creation or agent selection.
  src/coga/commands/uninstall.py: Use UTF-8 reads and LF state writes.
  src/coga/commands/update.py: Use UTF-8 reads and LF state writes.
  src/coga/compose.py: Use UTF-8 reads and LF state writes.
  src/coga/config.py: Check Windows Git-index context links and set UTF-8 child streams.
  src/coga/dream_cleanup_orphan_markers.py: Use UTF-8 reads and LF state writes.
  src/coga/dream_validate_drift.py: Use UTF-8 reads and LF state writes.
  src/coga/git.py: Share native locks, use Git path separators/index modes, and preserve directory refusal
    and LF publication.
  src/coga/github_preflight.py: Resolve Windows command wrappers before subprocess execution.
  src/coga/launch.py: Refuse unsupported agent work before state changes while retaining scripts and prompt
    reports; share native locks.
  src/coga/logfile.py: Read log text as UTF-8 and preserve slash-qualified nested task tags on Windows.
  src/coga/megalaunch.py: Refuse unsupported native agent sessions and write local selection state as
    UTF-8/LF.
  src/coga/open_pr.py: Resolve Windows command wrappers and write preparation artifacts as UTF-8/LF.
  src/coga/oscompat.py: Provide shared native lock directories, file locks and owned process trees with
    durable recovery probes.
  src/coga/paths.py: Distinguish missing workflow overrides from invalid file ancestors on Windows.
  src/coga/period_state.py: Use UTF-8 reads and LF state writes.
  src/coga/recurring.py: Use UTF-8 reads and LF state writes.
  src/coga/recurring_activity.py: Use UTF-8 reads and LF state writes.
  src/coga/recurring_autofix.py: Use UTF-8 reads and LF state writes.
  src/coga/recurring_clone.py: Use shared ProcessTree ownership, UTF-8/LF state, and descendant-aware
    Windows deadlines.
  src/coga/recurring_runner.py: Use shared process ownership and persisted native tree identities; preserve
    scripts during agent refusal and recover conservatively.
  src/coga/repl_supervisor.py: Make POSIX imports lazy on Windows and backstop agent spawning with the
    common refusal.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Sync the packaged topic
    with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Sync the
    packaged topic with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/sandbox-clone/SKILL.md: Sync the
    packaged topic with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Sync the packaged topic with
    its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: Sync the packaged
    topic with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Sync the packaged topic with
    its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Sync the packaged
    topic with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Sync the packaged
    topic with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Sync the packaged
    topic with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md: Sync the packaged
    topic with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md: Sync the packaged
    topic with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Sync the packaged topic
    with its canonical owner.
  src/coga/resources/templates/coga/bootstrap/skills/code/implement/seed_local_config.py: Sync the bundled
    skill or attachment with its live owner.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md: Sync
    the bundled skill or attachment with its live owner.
  src/coga/retire_worklist.py: Use UTF-8 reads and LF state writes.
  src/coga/skill.py: Use UTF-8 reads and LF state writes.
  src/coga/skill_manager.py: Use UTF-8 reads and LF state writes.
  src/coga/skill_update.py: Use UTF-8 reads and LF state writes.
  src/coga/ticket.py: Use UTF-8 reads and LF state writes.
  src/coga/usage.py: Use UTF-8 reads and LF state writes.
  src/coga/validate.py: Use UTF-8 reads and LF state writes.
  src/coga/views.py: Use UTF-8 reads and LF state writes.
  src/coga_edge/phone_home.py: Use UTF-8 reads and LF state writes.
  tests/conftest.py: Isolate and canonicalize Windows home/temp paths; share LF fixtures, executable,
    cleanup and skip helpers.
  tests/test_address_pr_comments_skill.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_aliases.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_atomicio.py: Retain POSIX mode assertions and exercise native UTF-8/LF atomic replacement.
  tests/test_authoring.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_autoclose.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_autoclose_dispose.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_autoclose_sweep.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_blackboard.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_blocker_reminders.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_bootstrap_ticket_skill_template.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_bootstrap_workflow_review_sections.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_branchcleanup.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_branchsweep.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_checkouts.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_clean_install_harness.py: Verify arbitrary-ref wheel walks and mark the Unix host-only driver
    tests.
  tests/test_cli.py: Exercise native agent refusals through cli.main with unchanged local/control state.
  tests/test_code_design_skill.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_code_implement_skill.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_commands.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_compose.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_config.py: Use native paths and homes, exercise context-link rejection and child UTF-8 streams.
  tests/test_create.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_done_marker_emission.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_dream_skill_scripts.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_dream_validate_drift.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_dream_worker_templates.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_edge_distribution.py: Use portable CLI stubs and distinguish Unix shell migration examples
    from native installed-wheel tests.
  tests/test_env_isolation.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_git.py: Cover Windows paths/index modes, CRLF clean-filter transactions and native publication
    refusals.
  tests/test_init.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_launch.py: Keep mocked orchestration portable; exclude only the real competing chat subprocess
    on Windows.
  tests/test_launch_auto.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_launch_restart.py: Use portable executable fixtures and exclude actual native agent REPL
    behavior pending the interactive ticket.
  tests/test_launch_script.py: Verify non-ASCII machine-readable script output and use portable native
    fixtures.
  tests/test_layout_contexts.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_logfile.py: Exercise nested path-derived audit tags and explicit UTF-8 log fixtures.
  tests/test_mark.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_megalaunch.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_notification.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_notification_messages.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_open_pr.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_open_pr_command.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_oscompat.py: Exercise real two-process lock contention, non-blocking errors, live owner probes
    and grandchild termination.
  tests/test_owner.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_packaging.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_paths.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_period_state.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_primitives.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_publish_state.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_recurring.py: Port native paths, Git fixtures and process ownership mocks while retaining
    POSIX signal tests.
  tests/test_recurring_activity.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_recurring_autofix.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_recurring_clone.py: Retain native Job Object tests and separate POSIX process-group expectations.
  tests/test_recurring_shims.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_reminders.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_repl_supervisor.py: Keep POSIX PTY coverage and apply the shared Windows interactive-ticket
    exclusion.
  tests/test_retire.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_retire_worklist.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_retro_skill_template.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_runner.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_secret.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_seed_local_config.py: Verify native clone config seeding with portable executable stubs and
    explicit POSIX-only permissions.
  tests/test_skill_manager.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_skill_update.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_smoke.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_status.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_taskfile.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_tasks.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_telemetry.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_ticket.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_uninstall.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_upstream_coga.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_usage.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_usage_report.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_validate.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_views.py: Use UTF-8/LF fixtures and native paths or stubs.
  tests/test_windows_clean_install.py: Keep native PowerShell argument round trips and separate the Unix
    host-driver check.
  tests/test_windows_process_recovery.py: Exercise live-owner inspection, interrupted-child cleanup and
    supervisor-death recovery on native Windows.
  tests/test_workspace_discovery.py: Use UTF-8/LF fixtures and native paths or stubs.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: This implement step does not perform code review; design approval is not code review. The later
    owner review remains required.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q
  status: passed
  head: 777c6bab056668afe6305f2c371f58aa7a44eabe
  base: d3b8e886ea293cc373f8f4be14061b2bc4738ebd
  detail: 'Full Linux suite after reconciliation: 4045 passed, 10 Windows-only skips, 408.72 s. No POSIX
    tests newly skipped or weakened. Only the projected ticket was dirty; code/tests matched this commit.'
- command: C:\Users\Administrator\.local\bin\uv.exe run --directory C:\Users\Administrator\coga-work python
    -m pytest -v -rs --tb=short --junitxml=C:\coga-clean-install\pytest-681e76db8-full17b.xml
  status: passed
  head: 681e76db81f11071a2a35d87df4609dda6096cd3
  base: c5ea1591e2874d79af2e330b2e3d3db8f0e4eb0c
  detail: 'Full native Windows suite: 3953 passed, 102 skipped, 7156.61 s, exit 0, no warnings; completed
    2026-10-23 08:14:35 UTC. Administrator S4U task preserved the run across SSH/tool restarts. Server
    2025, Python 3.11.17 (UTF-8 mode 0), Git 2.56.0.windows.3, autocrlf=true and no Bash. Only the installed
    Git ucrt64/bin directory was prepended to this test process PATH. Owner-approved temporary Defender
    exclusions covered the checkout, pytest temp and Git directories; all three were subsequently removed.
    XML/result/environment evidence: .coga/clean-install/win-core-20261022/pytest-681e76db8-*17b* and
    *-17b.*. Code/tests matched the committed tree.'
- command: |-
    git diff --name-only 681e76db81f11071a2a35d87df4609dda6096cd3 HEAD
    git diff --exit-code 681e76db81f11071a2a35d87df4609dda6096cd3 HEAD -- src tests scripts docs pyproject.toml uv.lock coga/context.md coga/skills coga/workflows
  status: passed
  head: 777c6bab056668afe6305f2c371f58aa7a44eabe
  base: d3b8e886ea293cc373f8f4be14061b2bc4738ebd
  detail: Reconciliation changed only five unrelated coga/tasks and coga/log.md paths. All runtime, test,
    fixture, harness, documentation and package-input content is identical to the full native pass and
    wheel walk. The historical receipts retain their actual OIDs; fresh Linux and native focus verify
    the reconciled commit.
- command: $env:PATH='C:\Program Files\Git\ucrt64\bin;'+$env:PATH; uv run --directory coga-work python
    -m pytest -q -rs --tb=short tests/test_oscompat.py tests/test_windows_process_recovery.py tests/test_cli.py::test_windows_agent_refusal_keeps_checkout_and_control
    tests/test_atomicio.py::test_atomic_write_and_ticket_round_trip_are_utf8_lf tests/test_launch_script.py::test_script_only_launch_is_headless_and_receives_task_contract
    tests/test_launch_script.py::test_open_script_step_fails_loud_when_no_agent_can_continue tests/test_launch_script.py::test_windows_prompt_report_allows_an_agent_ticket
    tests/test_launch_script.py::test_bootstrap_script_is_stateless_and_keeps_stdout_machine_readable
    --junitxml=C:\coga-clean-install\pytest-777c6bab0-focus18.xml
  status: passed
  head: 777c6bab056668afe6305f2c371f58aa7a44eabe
  base: d3b8e886ea293cc373f8f4be14061b2bc4738ebd
  detail: 'Fresh native verification after reconciliation: 26 passed, no skips/warnings, 29.22 s, exit
    0. Covers real process/lock recovery, unchanged-state CLI refusal, script/hybrid/prompt-report exceptions
    and UTF-8/LF.'
- command: AWS_PROFILE=coga-test ./scripts/clean-install/aws-windows.sh ssh win-core-20261022 uv run --directory
    coga-work coga --help
  status: passed
  head: 777c6bab056668afe6305f2c371f58aa7a44eabe
  base: d3b8e886ea293cc373f8f4be14061b2bc4738ebd
  detail: 'Fresh native CLI help at the reconciled commit: exit 0; /tmp/coga-windows-native-help18.txt.'
- command: AWS_PROFILE=coga-test ./scripts/clean-install/aws-windows.sh walk win-core-20261022 coga/windows-native-01-core-port-cli-and-test-suite-p-2e174f
    portwalk6 installer
  status: passed
  head: 681e76db81f11071a2a35d87df4609dda6096cd3
  base: c5ea1591e2874d79af2e330b2e3d3db8f0e4eb0c
  detail: 'Fresh local user portwalk6 installed the fetched branch wheel and passed all 16 steps through
    validate (ok_count 1, no fixes/issues, exit 0). Completed 2026-10-23 16:38 UTC. Wheel SHA256 c05b6ca582bc99c39f8224792ba4753c41e6e019392b56a006c39993ac951387;
    source and logs: .coga/clean-install/win-core-20261022/walks/portwalk6/.'
- command: |-
    cd tests/fixtures/seeded-repo/coga
    env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  head: 777c6bab056668afe6305f2c371f58aa7a44eabe
  base: d3b8e886ea293cc373f8f4be14061b2bc4738ebd
  detail: 'Seeded example fixture: ok_count 4, fixes [], issues [], exit 0; /tmp/coga-windows-example-validate18.json.'
- command: git diff --check
  status: passed
  head: 777c6bab056668afe6305f2c371f58aa7a44eabe
  base: d3b8e886ea293cc373f8f4be14061b2bc4738ebd
  detail: No whitespace errors.
- command: python -m pytest (full native Windows suite after the final state-only rebase)
  status: not-run
  detail: 'Not repeated for identical runtime, tests and package inputs: the preceding full native pass
    is preserved at its actual head/base, with the Git equivalence proof and fresh 26-test native check
    above. No Windows acceptance path was skipped to obtain a pass.'
- command: |-
    AWS_PROFILE=coga-test ./scripts/clean-install/aws-windows.sh teardown win-core-20261022
    AWS_PROFILE=coga-test ./scripts/clean-install/aws-windows.sh status win-core-20261022
  status: passed
  head: 777c6bab056668afe6305f2c371f58aa7a44eabe
  base: d3b8e886ea293cc373f8f4be14061b2bc4738ebd
  detail: Instance i-06604e1c1d0b18340 (us-east-1a), AMI ami-0b16ced290e00a1a3 / Windows_Server-2025-English-Full-Base-2026.10.14.
    Terminated 2026-10-23 17:11:29 UTC; security group/key deleted by 17:11:32. Status at 17:11:40 confirms
    terminated and no volumes or undeleted resources. Temporary tasks/processes and all three Defender
    exclusions were removed first. No resources from this run remain billing.
```

## Superseded designs

### 2026-10-23 — Original proposal and intermediate verification

Superseded by: the approved evaluator corrections and completed implementation above.
Reason: the native fix loop resolved the original open questions and failures;
retain the original proposal, review and intermediate evidence for traceability.

##### Dev

branch: coga/windows-native-01-core-port-cli-and-test-suite-p-2e174f


The blackboard is a notepad to be written to often as the human and agent works through a task.

##### Design notes (2026-10-19)

- The spec is under `## Description`. The source re-grep and the test-suite
  survey (a static read; nothing was run on Windows) are under `## Context`.
- Key decisions: (1) one new core module, `oscompat.py`, justified by a
  second consumer for each concern (the orientation lock in `launch.py` was
  missed in the original grep). (2) Refuse at the existing TTY gates, so
  `ticket.py`/script work keeps running on Windows and the refusal happens
  before any state change. (3) Coga writes LF everywhere.
- Harness gap: `walk` takes only `pypi|main`, so acceptance #2 (branch
  wheel) needs a small extension to `aws-windows.sh`.

##### Open Questions

2026-10-22 implementation session: the attending owner approved the evaluator
corrections, retained deterministic output at hybrid refusal, and the branch-wheel
walk extension. Keep user-repo `.gitattributes` out of scope and use polling
`msvcrt` locks. The owner also approved the default AWS instance; SSO was refreshed
and run `win-core-20261022` is provisioned. Teardown plus status is mandatory
before this session ends. Implementing agent: Codex (GPT-6; no explicit model
override in this session), not the ticket's configured Claude.

Baseline before implementation: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python
-m pytest -q` — 3987 passed, 7 skipped in 373.66s, Python 3.12. Added failing
regressions before fixes: seven CLI refusal/state-preservation cases and one
UTF-8 locale round trip (8 failures), plus shared OS tests (module absent).
Current main also requires migrating `checkouts.py`'s newly added flock consumer.

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

##### Evaluator review

2026-10-19 — **Needs corrections before implementation.** Reviewed the body
as the implementer's contract, then checked source, tests, owning topics and
the packaged `code/design-then-implement` workflow against main through
`47e9c5316`. Description/Context nesting is correct, and the frozen workflow
correctly hands this review to the owner. The three shared concerns have the
claimed consumers; the branch-wheel harness change fits this port. No design
approval is implied by completing this evaluation.

###### Must fix

1. **P1 — Port the persisted process-ownership proof, not only live child
   handles.** In `src/coga/recurring_runner.py`,
   `_run_repo_recurring` records `inner_pgid`; both
   `_cleanup_control_worktree` and `_stale_owned_control_worktree` call
   `_process_group_is_running(pgid)` independently of the proposed live
   `ProcessTree`. That helper still uses POSIX-only `os.killpg`.
   Stale recovery also calls `_process_is_running`, whose `os.kill(pid, 0)`
   is destructive on Windows: non-console-control signals use
   `TerminateProcess` ([Python 3.11 contract](https://docs.python.org/3.11/library/os.html#os.kill)).
   Extracting `_WindowsJob` verbatim does not supply this recovery proof.
   Specify a non-destructive Windows owner probe, the durable tree identity
   and its lifetime, and how normal cleanup and recovery after supervisor
   death establish that no descendant can still use the checkout. Add native
   Windows coverage for a live owner surviving inspection, interrupted-child
   cleanup, and stale recovery; preserve ambiguous ownership and transcripts.
   The existing contract is `coga-dev/internals/recurring-temp-worktrees`,
   sections "Cancellation and cleanup" and "SIGKILL survivors".

2. **P1 — Existing TTY gates are too late for the promised unchanged-state
   refusal.** `launch._LaunchInvocation._prepare_target` calls
   `_CheckoutBoundary.enter` before `_align_and_classify` and
   `_prepare_agent`; `enter` publishes dirty Coga state and prepares/switches
   the checkout. Direct `bootstrap/orient` does this before target lookup.
   Separately, `commands/ticket.ticket` calls `_resolve_or_create_target`
   (and `create_draft`) before `_run_authoring_session` checks its TTY, unless
   `--pick-agent` was used. Finally, `cli.main` sweeps on ordinary nonzero
   exits, so merely returning the new message still permits publication.
   Specify Windows refusal before these effects and how it suppresses the
   exit sweep. Test through `cli.main` with dirty Coga state, a feature
   checkout, and a new authoring title, comparing local and control state.
   Also delimit the promise for hybrid `ticket.py` runs: their script and
   lifecycle writes already happened when `_require_agent_after_script`
   refuses. State the retained-work/exit or pause behavior for direct and
   recurring launches, rather than promising no changes for both. Keep the
   script-only and prompt-report exceptions explicit.

3. **P2 — Specify UTF-8 reads and writes alongside LF.**
   `atomicio.atomic_write_text` writes UTF-8, but `Ticket.read` in
   `src/coga/ticket.py` and the forward readers in `src/coga/logfile.py` use
   `Path.read_text()` without an encoding; `commands/update.py` also has
   locale-default template/config reads and writes. Universal newlines fix
   line separators, not decoding: Python 3.11 text I/O otherwise uses the
   [locale encoding](https://docs.python.org/3.11/library/functions.html#open).
   A focused probe of `Ticket.write`/`Ticket.read` with a simulated cp1252
   default changed body text `Café` to `CafÃ©`. Define the state/template
   encoding contract and require non-ASCII read-modify-write coverage on
   Windows without an externally forced UTF-8 mode. LF-only ASCII assertions
   cannot establish the promised cross-platform byte preservation.

4. **P2 — Update the actual behavioral owners in the implementation PR.**
   Proposed shape §9 names the source map and harness topic, and conditionally
   `coga/sync`, which contains no `flock` specification. The lock contract is
   `docs/contexts/coga-dev/internals/launch-claims/SKILL.md`, "The local state
   lock". The changed refusal/ordering and hybrid contracts belong in
   `coga/launch`, `coga/checkouts/launch-boundary`, `coga/tickets/authoring`,
   `coga/script-tickets` and `coga/recurring/scheduling/failures`; the
   process-recovery change belongs in `coga-dev/internals/recurring-temp-worktrees`.
   Add the affected owners to the deliverables, with one owner per fact and
   links from related topics. Keep packaged twins for the user topics and
   the `coga/testing/clean-install/windows-aws` skill; development topics
   have no twins. This follows
   the repo's same-PR knowledge rule without pulling `coga/install` into scope.

###### Optional recommendations

- Correct the "Step 1 alone" smoke milestone: `git.py` and `launch.py`
  independently import `fcntl` until §2, so guarding only the supervisor and
  megalaunch modules cannot make `coga --help` import on Windows.
- Make the shared Windows skip helper accept a specific reason: the example
  marker's interactive-ticket reason does not describe Unix host-harness or
  permission tests. Keep mocked orchestration tests runnable where possible
  (for example `test_megalaunch.py::repo` already stubs the TTY gate), and
  reserve native refusal tests for the real platform predicate.
- Exercise CRLF checkouts explicitly despite the fixture default of
  `core.autocrlf=false`; preserve exact transaction guards while testing their
  existing Git clean-filter semantics. The native fresh-user walk retains
  Git for Windows' default `core.autocrlf=true`.

###### Verification and limits

Focused existing Linux regressions passed: **8 passed in 9.26s**, using:

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q \
  tests/test_ticket.py::test_ticket_requires_tty_before_spawning \
  tests/test_ticket.py::test_ticket_pick_agent_requires_tty_before_scaffolding \
  tests/test_launch.py::test_launch_prepares_a_feature_checkout_and_resolves_a_ticket_created_on_control \
  tests/test_launch.py::test_orientation_prepares_control_before_resolving_local_override \
  tests/test_cli.py::test_withheld_launch_return_skips_the_sweep_and_keeps_the_exit \
  tests/test_cli.py::test_launch_entry_refusal_through_main_skips_the_sweep
```

`PYTHONPATH=/home/n/Code/coga/src .venv/bin/coga validate --task windows-native/01-core-port-cli-and-test-suite-pass-on-native-window --json`
reported `ok_count: 1` and no issues. `git diff --check` passed; a byte comparison
confirmed the original body, frontmatter and blackboard were preserved.

The encoding probe used a temporary file and simulated the reader's default
encoding on Linux; it was not native Windows evidence. No Windows instance
was provisioned and neither full suite was run in this design-review step.
No ticket-body, implementation, branch or PR changes were made.


##### Implementation progress (2026-10-22)

- Windows AWS run `win-core-20261022` is provisioned under the approved default.
  Windows Server 2025, Python 3.11.17, Git 2.56.0.windows.3. Administrator has
  no bash on PATH; Python UTF-8 mode is off. Teardown remains mandatory.
- First pushed implementation `8e990e56f0f8b06cf73435eb1b2ba1f1c575888f`
  passed the full Linux suite: `PYTHONPATH=/home/n/Code/coga/src
  .venv/bin/python -m pytest -q` — 4000 passed, 7 skipped, 390.12 s.
- Native evidence found CRLF blank `.gitignore` lines misclassified as an ignore
  match, a module-level test SIGKILL reference, redirected cp1252 CLI output,
  and Windows executable lookup for .cmd test stubs. The repository's own
  `.gitignore` is now LF; user-repo `.gitattributes` seeding stays out of scope.
- Native focused checks at `33b83905c823578b5048462d019826153c6312d9`:
  108 passed, 39 failed, 3 skipped (315.55 s). Lock contention, non-destructive
  process inspection, unchanged-state command refusal, config seeding, and
  UTF-8/LF file round trips passed. Failures identified missing `.cmd` lookup
  and a venv launcher handle outside the owned Job Object; fixes are in progress.
- The second full Linux run had 4001 passed, 10 skipped and one fixture failure:
  staging reset an index-only executable bit on POSIX. Preserve the original
  chmod case on POSIX and use the index on Windows; rerun before handoff.
- New Windows-only recovery tests cover a surviving live owner, interrupted
  child cleanup and supervisor death with a grandchild plus retained transcripts.
  Shared Windows skip reasons distinguish PTY/agent work, Unix modes and Unix
  host/runbook scripts. Native Job Object tests are never skipped on Windows.

- At `c508a28bab66166bf4f6187b6ff7952de98e813a`, the full Linux suite passed:
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q` —
  **4008 passed, 10 skipped, 374.80 s**. The three added Linux skips are
  native Windows recovery tests; existing POSIX coverage remains enabled.
  Native `coga --help` passed and focused ownership/recovery tests passed
  **9 tests in 23.99 s**. The Job Object startup now queries active members,
  because a Windows venv launcher is not the actual interpreter in the job.
- Fresh-user branch-wheel walk `portwalk2` passed through validation
  (`ok_count: 1`, no issues), wheel SHA-256
  `7d5f6dede1ab85d6eb280fc9e80cade5a970bd7b8f919a4c81e42ff2162ea2c0`.
  The walk builds from fetched `c508a28bab66166bf4f6187b6ff7952de98e813a`.
  Final-head evidence is still needed after subsequent fixes.
- Native script/clone/validation diagnostics at that head: **217 passed,
  18 failed, 6 skipped, 236.51 s**. Failures expose Git path separators and
  executable-mode assumptions in `git.relative_to_root`, `git._build_tree`
  and checkout proofs; a detached child's lifetime must also count toward
  `recurring_clone._drain_clone_script`'s Windows deadline. Fixes retain
  POSIX behavior and use the Windows Git index for executable modes.
  Test-only failures also require portable paths, UTF-8 subprocess decoding,
  read-only Git fixture cleanup and deterministic local line-ending config.
  Full native acceptance remains pending; no success is claimed for it.

###### Confirmed implementation decisions

The attending owner approved the evaluator-corrected approach and the default
Windows instance before implementation. The four design questions are resolved:
pre-entry Windows classification admits locally visible deterministic scripts
and prompt reports, while refusing agent work before checkout/publication;
init's user-repo `.gitattributes` policy remains out of scope; locks use stdlib
`msvcrt` polling; the harness accepts a fetched branch ref for its wheel walk.
Hybrid scripts keep their completed work and lifecycle writes when a later
agent phase refuses; direct launch exits nonzero and recurring uses its existing
agent-refusal pause path. This retained work is outside the unchanged-state
promise for an entry refusal.

Windows ownership uses a random globally named Job Object persisted in marker
version 3. Inspection uses non-destructive process handles and active-job
queries. The supervisor owns the retained kill-on-close handle; descendants
cannot escape when their immediate parent exits. Uncertain or legacy ownership
keeps the checkout and transcripts instead of guessing that cleanup is safe.

The c508 diagnostic full-suite attempt stopped at its configured failure limit:
**35 failed, 479 passed, 3 skipped, 1232.10 s**. It is diagnostic evidence only,
not full-suite acceptance. The next revision fixes its reported path, mode,
UTF-8 decoding, fixture cleanup and mocked-agent-gate failures. Current main
also advanced; reconciliation precedes the next push.

###### Rebased verification (iteration 4)

- Tested/pushed head: `351b0ca25de2a1c3cbffded8551dc3c87dc922af`; merge base/current fetched main:
  `6f41139a22a2d4d80dff386418ddbcb98c24856e`. Reconciled main's topic trimming and Git diagnostic/log changes;
  ported the newly added test fixtures' text I/O too. The projected ticket
  was backed up, verified and restored unstaged byte for byte.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q`:
  **4036 passed, 10 skipped in 382.51 s**. Implementation paths exactly match
  the committed tree (only this projected ticket is dirty).
- From `tests/fixtures/seeded-repo/coga`,
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json`:
  **ok_count 4, issues []**. The inherited legacy Slack variable was unset
  for this fixture-only validation; no config or secret was changed.
- Native `uv run --directory coga-work coga --help` passed at this head.
  Four disjoint native diagnostic batches cover all top-level test modules;
  final full-suite acceptance is still pending. The owner approved two temporary Defender exclusions, now applied and
  verified: `C:\Users\Administrator\coga-work` and
  `C:\Users\Administrator\AppData\Local\Temp\pytest-of-administrator`.
  Remove both and verify their removal before teardown. Diagnostic batches
  span that environment change; final acceptance will use a stable setup.


###### Native diagnostic corrections (iterations 5–6, ongoing)

- Pushed `a4b7d87d70321fa37543864901c3abbdf6d96c95` on unchanged main/base
  `6f41139a22a2d4d80dff386418ddbcb98c24856e`. Windows is still running the
  diagnostic batches at `351b0ca25de2a1c3cbffded8551dc3c87dc922af`; do not
  change its checkout until those test processes finish.
- Native group 4 stopped at its diagnostic limit: **40 failed, 957 passed,
  46 skipped, 1017.72 s**. Its continuation stopped at the same limit:
  **40 failed, 819 passed, 39 skipped, 5 warnings, 610.38 s**. The second
  continuation finished with **1 failed, 64 passed, 2 skipped, 58.43 s**;
  its usage-report failure is the script encoding/CRLF output issue fixed locally. Other groups remain running.
- Native findings and corrections: Windows Git materializes index symlinks
  as regular files (`config.require_context_artifact` now checks the index);
  `paths.resolve_workflow_path` must distinguish a file ancestor from a
  missing override despite Windows ENOENT; child Python script streams need
  UTF-8 (`config.build_launch_env`) while locale-default file decoding stays
  unchanged. A raw-byte native `retire --help` probe confirmed mixed cp1252
  child output and UTF-8 launcher output with `sys.flags.utf8_mode == 0`.
  `authoring.snapshot_authoring_files` must fingerprint Git index modes on
  Windows. These corrections are committed in
  `b414edb3fbed96af6272496c8a235f051ec39925`; its full Linux run is in progress.
- Fixture corrections preserve assertions: native HOME/USERPROFILE pairs,
  Git's slash-separated paths, repr-escaped Windows diagnostic paths,
  percent-encoded worklist paths, mocked agent-platform gates and executable
  lookup signatures, and moving cwd before deleting its directory.
- Full Linux diagnostics passed twice: **4036 passed, 10 skipped, 361.19 s**
  and **4036 passed, 10 skipped, 355.21 s**. Local edits continued during
  those runs, so neither is a final committed-tree receipt. Focused checks:
  **319 passed in 18.00 s** (script/config/path/retire/Git/packaging),
  **94 passed in 2.93 s** (authoring/worklist/mode publication).
- All three owner-approved Defender exclusions are now active and verified:
  the Administrator checkout, pytest temp directory, and `C:\Program Files\Git`.
  Remove all three and verify removal before teardown. Ten native `git --version`
  calls took 2.79 s while Defender used 1.94 CPU-seconds.
- Full native acceptance, final-head Linux verification, a final-head
  fresh-user branch-wheel walk, teardown/status, structured PR preparation
  and the implement bump all remain outstanding. No PR has been opened.
- The native diagnostics also found two platform-specific recovery-hint
  assertions and a real competing `coga chat` subprocess test. Keep its POSIX
  behavior and use the shared interactive-ticket exclusion on Windows;
  standalone orientation-lock contention/process-death tests remain enabled.
- Full Linux verification of `b414edb3fbed96af6272496c8a235f051ec39925`
  passed **4037 tests, 10 skipped, 359.31 s**, with only the projected ticket
  dirty. Main is still `6f41139a22a2d4d80dff386418ddbcb98c24856e`.
  A native probe confirmed Git 2.56 refuses `update-ref FETCH_HEAD`; the
  owner-probe fixture now populates it with an actual local fetch instead.
- Pushed `5c6c4c590615ab700a1ad3e68f4052b7ff546272` after another exact-tree
  Linux pass: **4037 passed, 10 skipped, 359.49 s** (same full-suite command
  and merge base). Native diagnostics subsequently exposed a real audit bug:
  `logfile.ref_tag_for_path` produced backslash-separated nested tags, so
  recurring sync failures disappeared from slash-qualified task history.
  The correction uses `Path.as_posix()`, with nested file/task/template cases
  and the ticket-discovery owner/twin updated; **51 focused tests passed**.
- Native Git startup probe (15 calls each, while diagnostics ran): the
  installed `cmd/git.exe` wrapper took 3.30 s; its `ucrt64/bin/git.exe` took
  1.89 s. Prepending that installed binary directory only for a later test
  process still leaves Bash absent; no machine PATH or security setting is
  changed by the probe. The fresh-user walk keeps the installer defaults.
- `b887e5db9ce46665e8c956bf4b644bc1415fea88` passed the full Linux suite:
  **4040 passed, 10 skipped, 359.02 s**, on unchanged main/base, before any
  subsequent fixture edits. The native probe directly confirmed the old
  `recurring\weekly-check` tag. Four later init fixture failures need native
  executable lookup and path-aware symlink comparisons; their focused Linux
  check passed **4 tests in 8.30 s**. Native batches are still on `351b0ca25`.
- Full Linux verification of `634b75a52d2c65faec25228ec858ce71577b8c82`:
  **4040 passed, 10 skipped, 373.39 s**. Later native fixture corrections
  preserve quoted recovery paths, test Windows mode changes through the Git
  index, compare promoted links with their original native targets, and use
  a valid Windows filename for real rename coverage. A filesystem-free PR
  rendering case keeps pipe-character escaping covered on both platforms.
  These focused checks passed **9 tests in 11.44 s**.
- `c5edf2882c2eed96b6430a218e4e559936dd0c51` passed full Linux verification:
  **4041 passed, 10 skipped, 384.71 s**; only the projected ticket was dirty.
  Fetched main is still `6f41139a22a2d4d80dff386418ddbcb98c24856e`.
  Native diagnostic group 2 completed at `351b0ca25`: **18 failed, 678 passed,
  6 skipped, 4702.15 s**. Every reported failure has a corresponding local
  correction awaiting native re-verification. Groups 1 and 3 still run.
- The native direct-Git PATH smoke passed **2 tests in 34.78 s** at `351b0ca25`:
  the failing-clean-filter Git test and `test_open_pr_opens_and_records_url`.
  This verifies real Git helpers and mocked-GitHub publication through the
  installed `ucrt64/bin/git.exe`; the process PATH still contains no Bash.
- The remaining native diagnostic SSH sessions ended with transport exit 255
  when the host public IP changed. AWS reported both instance checks healthy;
  the existing port-22 rule was replaced with the current single-host /32.
  Reconnection found no surviving Python/Git/uv test processes. Groups 1 and 3
  are incomplete diagnostics, not passing receipts. Retrying the pushed fixes
  at `c5edf2882c2eed96b6430a218e4e559936dd0c51`; no code edits were lost.
- Latest native checkout is `c5edf2882c2eed96b6430a218e4e559936dd0c51`.
  `coga --help` exited 0. Environment verification: Python 3.11.17,
  `sys.flags.utf8_mode == 0`, Bash absent from PATH, system
  `core.autocrlf=true`. The 62 focused lock/process/context/log/Unicode/init/
  recovery/PR cases finished: **62 passed in 185.60 s**, exit 0.
  The full unpartitioned native `python -m pytest -v -rs --tb=short
  --junitxml=C:\coga-clean-install\pytest-c5edf2882.xml` is now running,
  with only the installed direct Git binary directory prepended to test PATH.
- Fresh-user branch-wheel walk passed at `c5edf2882c2eed96b6430a218e4e559936dd0c51`
  as `portwalk4`: version, init and validate all succeeded, validation
  `ok_count: 1`, no fixes/issues, exit 0 at 2026-10-23 01:49 UTC.
  Wheel SHA-256: `65b7944606c9055d652413ed9f19036464c8714e81d769c03a3b25de57a6f46a`.
  Evidence: `.coga/clean-install/win-core-20261022/walks/portwalk4/`.
  The preceding `portwalk3` attempt stopped on the host's read-only uv cache
  before creating a Windows user; the successful retry used approved cache
  access and a new evidence directory. Native full-suite verification continues.
- The previously unvisited recurring tail exposed two more fixture failures:
  moving/removing the current directory is prohibited on Windows. The deep
  monorepo and root-layout fixtures now leave that directory before relocation;
  their focused Linux run passed **2 tests in 4.33 s**.
- Main advanced through PR #1091 (task-only prompt loop), to
  `11f8d3c72412ef10952935a8ff902ba99bd0f06b`. Rebased cleanly and preserved the
  projected ticket byte-for-byte from a verified external backup (SHA-256
  `2ba8c82af1fd7cb506d1268c8c134fc75e42794e1a887c10788fe2efcb7a81dd`).
  New local head is `d42a38172f3df897e2062f05854d4d7317cd7135`; full Linux
  verification is running. Windows stays at `c5edf2882` until its diagnostics
  finish. Its walk/full-suite receipts are historical after this reconciliation.
- Rebased Linux run at `d42a38172f3df897e2062f05854d4d7317cd7135` finished:
  **3 failed, 4041 passed, 10 skipped, 379.66 s**. All failures originate in
  main's subsequent state-sync `11f8d3c72`: two principles-composition cases
  conflict with its shortened `coga/context.md`; packaging reports stale CLI
  and architecture twins. Asked the owner whether to restore the generated
  principles copy or keep the shorter context and update tests. This is
  pending; PR #1091 explicitly described the generated copy as retained.
- The additional native recurring/recovery batch at `c5edf2882` finished:
  **4 failed, 259 passed, 7 skipped, 387 deselected, 734.33 s**. Besides the
  two committed directory-relocation fixture corrections, one summary assertion
  needs a native Path. The Windows descendant-after-parent-exit test returned 0
  instead of timeout 124 and reproduces alone; investigating before changing
  runtime behavior or its assertion. The stale full native run was stopped at
  **471 passed, 3 skipped, no failures yet**; verified its processes are gone.
- Native diagnosis isolated the parent-exit failure to the wrapper's venv
  launcher: plain subprocess descendants survived; the Coga-wrapped descendant
  died early and the runner returned 0 in 0.51 s. Using the base interpreter
  only for the stdlib wrapper made **10 native checks pass in 7.93 s**, including
  both clone timeout variants, real locks and crash recovery. The requested
  script interpreter/environment remain unchanged. Added a direct ProcessTree
  parent-exit regression and updated the recurring-clone implementation owner.
- Pushed reconciled head `a621eb93b8248911483349459951fa6bccc40990`, based on
  `11f8d3c72412ef10952935a8ff902ba99bd0f06b`. It includes the native path assertion
  and the two packaged-topic refreshes. Focused Linux verification passed
  **37 tests, 2 Windows-only skips, 10.73 s**; the packaging/summary pair passed
  **2 tests in 1.45 s**. Full Linux verification and native committed-code
  re-verification are underway. The principles-context decision remains pending;
  `coga/context.md` and its existing assertions are still unchanged from main.
- Full Linux verification at `a621eb93b8248911483349459951fa6bccc40990`:
  **2 failed, 4043 passed, 10 skipped, 357.41 s**. Only the pending principles
  context conflict fails; packaging is now green.
- Committed-code native focus at that head: **1 failed, 41 passed, 2 skipped,
  89.87 s**. All original cases passed; the new ProcessTree test asserted death
  immediately after job accounting reached zero. A native probe showed the
  process still signaled as live immediately, then dead 10 ms later, with no
  surviving Python process. Added a bounded termination wait (same pattern as
  the existing crash-recovery tests); **6 focused Linux tests passed in 0.49 s**.
  Native full verification still must run after this correction, and the
  principles-context owner answer is still pending.
- Owner decision: restore the generated principles copy in `coga/context.md`
  and keep its existing tests. This resolves the main state-sync conflict;
  PR #1091's task-only prompt loop remains intact.
- Native kernel/recovery check at `3080066c486f6f861655751f392958b53fd137bb`:
  **1 failed, 10 passed, 9.37 s**. The crash-recovery case asserted stale
  ownership immediately after only the grandchild had exited; its isolated
  rerun passed **1 test in 2.38 s**. The test now waits boundedly for both
  grandchild exit and the existing conservative owner/tree recovery proof.
  Production ownership checks and all final assertions are unchanged.
- Full Linux verification of `3080066c486f6f861655751f392958b53fd137bb`
  finished **2 failed, 4043 passed, 10 skipped, 367.67 s**, only the now-resolved
  principles conflict. The restored principles pair passed **2 tests in 8.03 s**;
  packaging/process focus passed **36 tests, 3 Windows-only skips, 3.89 s**.
- Pushed and checked out `78d5272ed163be58863464fd5937597c4e4ad78f`, based on
  unchanged main `11f8d3c72412ef10952935a8ff902ba99bd0f06b`. Native `coga --help`
  exits 0 and all **11 lock/process/crash-recovery checks pass in 9.24 s**.
  Full Linux and full unpartitioned Windows verification are running. The
  native command is `uv run --directory coga-work python -m pytest -v -rs
  --tb=short --junitxml=C:\coga-clean-install\pytest-78d5272ed.xml`, with only
  the installed direct Git binary directory prepended to its process PATH.
- Full verification at `78d5272ed163be58863464fd5937597c4e4ad78f`: Linux
  **4045 passed, 10 skipped, 360.58 s**; Windows **23 failed, 3930 passed,
  102 skipped, 1 warning, 6388.09 s**. The failures were fixture portability:
  a missing `true` stub, native path assertions, unescaped Windows paths in
  TOML/JSON fixtures, and a cloned fixture inheriting `core.autocrlf=true`.
  The installed-wheel embedding probe also needed its UTF-8 pipe encoding
  explicitly supplied to its Python child (the test bypasses `cli.main`).
- Adjacent issue, not changed here: `commands/uninstall.py::_uninstall_via_tool`
  displays POSIX `VAR=value command` syntax for its manual fallback even on
  Windows. The real subprocess receives the correct environment and its tests
  pass after native path normalization; a PowerShell/cmd-ready recovery hint
  remains follow-up work. No existing follow-up ticket was found in this step.
- Fixture correction focus passed **73 tests in 13.63 s** on Linux.
  Reconciled main's three new competition-testing tickets (no behavior changes),
  preserving the projected ticket byte-for-byte from a verified external copy.
  Pushed rebased head `b984972a5ad89a16fbeed3fc4df589d858d4cfd2`, merge base
  `c5ea1591e2874d79af2e330b2e3d3db8f0e4eb0c`. Fresh Linux full-suite and
  native re-verification are underway. The preceding final walk invocation
  was interrupted before execution; `portwalk5` has not been created.
- Native focus at `b984972a5ad89a16fbeed3fc4df589d858d4cfd2` passed
  **73 tests in 77.90 s**, with no warnings. The retried checkout succeeded
  after replacing the SSH rule's old single-host /32 with the host's new /32;
  its scope was not widened. Native environment: Python 3.11.17, UTF-8 mode 0,
  Bash absent, Git `core.autocrlf=true`, 26.1 GiB free.
- Fresh-user branch-wheel walk as `portwalk5` passed every step through
  `coga validate --json` (ok_count 1, no fixes/issues), exit 0. Source is
  `b984972a5ad89a16fbeed3fc4df589d858d4cfd2`; wheel SHA-256
  `c05b6ca582bc99c39f8224792ba4753c41e6e019392b56a006c39993ac951387`.
  Full native verification is now running with XML receipt
  `C:\coga-clean-install\pytest-b984972a5.xml`; all earlier failed/partial
  receipts remain historical. Full Linux verification is still running.
- Full Linux suite at `b984972a5ad89a16fbeed3fc4df589d858d4cfd2` passed:
  **4045 passed, 10 skipped, 399.29 s**. Only the projected ticket is dirty;
  base remains `c5ea1591e2874d79af2e330b2e3d3db8f0e4eb0c`. Seeded-fixture
  validation reports **ok_count 4, fixes [], issues []**; native help exits 0.
  Final native suite, Defender exclusion removal, teardown/status and handoff
  are the remaining acceptance work.
- The tool server restarted during the full Windows run. Its SSH process
  ended at **1647 passed, 48 skipped, no test failures**, before completion;
  remote inspection found no surviving Python/Git/uv processes. This is an
  interrupted diagnostic, not a full-suite pass. Main is still unchanged.
- Retrying the same full suite at the unchanged head through a temporary
  Administrator S4U scheduled task (`Coga-Windows-Port-Pytest-16b`) so host/SSH
  restarts cannot end it. The runner checks the exact commit, user/home,
  UTF-8 mode off, no Bash and default autocrlf before starting pytest, and
  records stdout, stderr, JUnit XML and the actual exit code in
  `C:\coga-clean-install\pytest-b984972a5-*16b*`. No repository code or
  test settings changed. Remove the temporary task during final cleanup.
- The scheduled retry's environment probe passed: Administrator, home
  `C:\Users\Administrator`, exact head `b984972a5ad89a16fbeed3fc4df589d858d4cfd2`,
  Python 3.11.17 with UTF-8 mode 0, direct Git binary, Bash absent and
  `core.autocrlf=true`. The first 217 tests passed, with 3 expected skips.
  Poll using `/tmp/coga-windows-poll16b.py`; it reconnects briefly and reads
  the remote log/result, so the full run does not depend on a live tool session.
- The scheduled retry exposed fixture spelling rather than a runtime defect:
  Task Scheduler uses `Administrator`, while the existing pytest directory
  is `pytest-of-administrator`; Git reports the actual canonical spelling.
  Seven recovery-message/path assertions failed. Shared tmp/HOME/TEMP paths
  and the two direct temp-factory consumers now resolve their spelling;
  assertions and POSIX coverage remain intact. The testing owner documents it.
  Initial focused Linux verification passed **109 tests in 37.24 s**.
- Pushed/checked out `681e76db81f11071a2a35d87df4609dda6096cd3`, based on
  unchanged `c5ea1591e2874d79af2e330b2e3d3db8f0e4eb0c`. Full Linux verification
  is running. Temporary Administrator task `Coga-Windows-Port-Pytest-17`
  first runs the seven affected native cases, then the complete suite if
  they pass. Poll `/tmp/coga-windows-poll17.py`; remote receipts use
  `C:\coga-clean-install\pytest-681e76db8-*17*` and include the active root PID.
  All older scheduled tasks were removed. Stopping a scheduled PowerShell
  action alone left its uv child running; explicitly stopped that owned
  process tree and verified no Python/Git/uv process remained before this retry.

- Final unpartitioned native run at `681e76db81f11071a2a35d87df4609dda6096cd3`
  completed successfully through temporary Administrator task
  `Coga-Windows-Port-Pytest-17b`: **3953 passed, 102 skipped, 7156.61 s**, exit 0,
  no warnings. Python 3.11.17, UTF-8 mode 0, no Bash on PATH, default
  `core.autocrlf=true`. The preceding seven fixture regressions passed in 46.42 s.
  Full Linux: **4045 passed, 10 skipped, 354.43 s**. The native XML and runner
  result were copied to `.coga/clean-install/win-core-20261022/`; the skip list
  exactly matches the recorded 40 interactive and 62 POSIX/host cases.
- Fresh-user branch-wheel walk `portwalk6` passed all 16 steps through validate
  at the same head (ok_count 1, no issues/fixes, exit 0). Native help also passed.
- Reconciled main through `d3b8e886ea293cc373f8f4be14061b2bc4738ebd` and pushed
  `777c6bab056668afe6305f2c371f58aa7a44eabe`. Only five unrelated ticket/log paths
  differ from the full native test head; all implementation, tests, docs,
  harness and package inputs are identical. Historical receipts keep their
  actual head/base. Fresh full Linux, native admission/lock/recovery/script
  checks and help are running on the rebased head. Seeded validation passed
  (ok_count 4, no fixes/issues).
- AWS SSO remains expired as of 2026-10-23 16:43 UTC; asked the attending owner
  to refresh it for teardown. SSH is available. The instance still exists;
  scheduled-task removal, all three approved Defender exclusion removals,
  teardown/status and final handoff remain mandatory before bump.

- Fresh checks on `777c6bab056668afe6305f2c371f58aa7a44eabe`: native focus
  **26 passed in 29.22 s**, no skips/warnings; native help exit 0. The native
  XML was copied locally. Removed `Coga-Windows-Port-Pytest-17b` and verified
  no temporary Coga test tasks or Python/uv/Git processes remain. Removed all
  three approved Defender exclusions and verified unrelated exclusions were
  preserved. Evidence: `/tmp/coga-windows-task-cleanup18.txt` and
  `/tmp/coga-windows-exclusions-removed18.txt`. AWS teardown still awaits SSO.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`
Recorded: 2026-10-23T17:41:49+00:00

    Branch 'coga/windows-native-01-core-port-cli-and-test-suite-p-2e174f' is not safe to publish. refs/heads/coga/windows-native-01-core-port-cli-and-test-suite-p-2e174f does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase origin/main`. Reconcile it and relaunch, or `coga block --task windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`.
