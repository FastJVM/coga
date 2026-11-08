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
step: 5 (open-pr)
agent: claude
---

## Description

Make interactive agent sessions work on native Windows, then declare Windows
supported. That covers `coga launch` of an agent step, `coga chat`,
`coga build`, `coga ticket`'s authoring session, and `coga megalaunch`
with its picker. This is the last of the three port tickets. It
builds on `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`,
which makes every module import on Windows, adds `src/coga/oscompat.py`
(`lock_dir`, `lock_fd`, `ProcessTree`), and makes every agent-session
surface refuse on Windows with one "not supported yet" message. **Do not
start the implement step until that ticket is merged**. If its merged shape
differs from its spec (for example `ProcessTree`'s interface), adapt this
design to what landed, and note the delta on the blackboard.

Evidence from the box (2026-10-19, Server 2025 build 26100, Claude Code
2.1.304, Windows OpenSSH; the full record is on the blackboard) settled the
PTY question. The agent does **not** need a PTY on Windows. When the child
inherits the supervisor's console (sshd's ConPTY over `ssh -t`, or a local
Windows Terminal/conhost), Claude Code's TUI renders and takes arrows and
Enter. A kill-on-close Job Object owns the whole tree, CTRL_BREAK makes
Claude exit on its own in about 0.25 s, and nothing is left running. A
`pywinpty` ConPTY proxy also worked, but it costs a Windows-only wheel,
proxy threads and console-mode juggling, and CTRL_BREAK cannot cross the
inner ConPTY, so every teardown became a hard kill. The owner chose the
inherited console (2026-10-19).

The cost of that choice is that the supervisor cannot see the agent's
output, so **idle-timeout cannot be measured on Windows**. The owner chose
fail-loud (2026-10-19): an explicit `--idle-timeout` refuses on Windows, and
callers that arm it from defaults or config run with `max_session` only,
after one visible warning.

The fix loop is the core ticket's: harness box, `checkout`, run over SSH,
fix, repeat. Run the full Linux suite on every iteration, and end every
session with `teardown` plus `status`.

### Acceptance criteria

- [ ] **Attended launch over SSH, run by the agent itself.** On a fresh
      box, after harness `checkout` of the branch, Claude Code is installed
      (native installer) and authenticated. `coga launch <agent-step ticket>`
      runs over `ssh -tt`, driven from a host-side PTY. The REPL renders and
      takes input. When the session's agent runs `coga bump`, the session
      ends: `[coga watcher]` reports the done trigger, `coga launch` exits 0,
      and the ticket advanced exactly one step to an owner-held step.
      Use separate disposable tickets for `coga mark done` (task becomes
      done) and `coga block` (task becomes blocked with the requested reason);
      both report the done trigger and exit 0. After each run, the Job's active
      process count is 0, and `tasklist` shows no `claude.exe` and no node
      or bash children left by the session. The console input/output modes
      after the launch equal the modes before it.
- [ ] **Chaining.** A two-agent-step workflow chains on Windows: after the
      first step's bump, the supervisor spawns the second step's session in
      the same `coga launch`.
- [ ] **Liveness on Windows.**
      - `coga launch --max-session N` tears a session down at N seconds
        with exit 124 and kind `timeout`.
      - `coga launch --idle-timeout N` exits 2 before any state change,
        with a message naming the Windows limitation and `--max-session`.
        The final CLI state sweep is withheld: pre-existing dirty files,
        the index, checkout branch, local HEAD and remote tip are unchanged.
      - A Python caller that passes `idle_timeout` (megalaunch, recurring)
        gets one `[coga watcher]` warning that idle-timeout is unavailable
        on Windows, and the session runs with `max_session` only.
- [ ] **Interrupts.** While a Windows session runs, Ctrl+C reaches the
      agent as input (Claude Code shows its own "press again to exit"), and
      the `coga` parent does not raise `KeyboardInterrupt`. Closing the SSH
      connection mid-session leaves no orphaned agent processes, because
      the Job is kill-on-close.
- [ ] **Exit codes on native Python 3.11.** Ordinary nonzero exits,
      CTRL_BREAK termination, and an NTSTATUS error retain their complete
      32-bit value through the interactive wrapper and the outer Coga CLI
      process. A crash racing a matching sentinel remains `crash` with
      `done_signalled=True`; done and timeout retain their defined 0/124
      outcomes when there is no independent crash.
- [ ] **Megalaunch picker** works over `ssh -tt`: ↑/↓/j/k move, Space
      toggles, `a`/`n` select all/none, Enter confirms, and `q`/Esc/Ctrl+C
      quits. Ctrl+C also quits during idle polling and redraw, with no
      traceback, saved selection, or launch. Console modes and prior signal
      handlers are restored on confirmation, cancellation, and failure.
      A terminal resize redraws within about 0.2 s.
- [ ] **Large prompts.** A composed prompt larger than the Windows
      command-line budget reaches the agent through the existing
      prompt-file pointer, not a `CreateProcess` failure. An agent CLI that
      resolves to a `.cmd`/`.bat` shim (npm-installed Codex) always gets
      the pointer. Budgets cover the actual serialized agent, wrapper,
      and shell command lines, including their terminating NUL, rather
      than the unquoted prompt alone. Shell-sensitive paths and arguments
      must round-trip losslessly through fake `.cmd` and `.bat` agents
      (owner, review-design, 2026-10-19); a character allowlist that
      refuses those inputs is not the chosen solution. Raw CR/LF in
      non-prompt batch arguments is the specific accepted exception:
      refuse in preflight, identifying the argument and suggesting a native
      executable or removing those line breaks. Multiline prompts stay in
      the file; the generated pointer uses the line separators in §5.
- [ ] **The core ticket's refusal is gone.** `agent_sessions_supported()`
      and its message, every caller of it, and `spawn_agent_session`'s
      Windows backstop are deleted. Every test the core ticket skipped
      with the shared `windows_interactive_skip` marker either runs on
      Windows or is replaced by a Windows equivalent, and the marker
      itself is deleted. POSIX-only tests of PTY mechanics (`pty.fork`,
      `TIOCSWINSZ`, SIGWINCH) may keep a plain `os.name != "posix"` skip
      if a Windows-run equivalent of the same contract exists, and each
      one is listed in the PR.
- [ ] **Suites.** The full `python -m pytest` passes natively on a fresh
      box and on Linux. No POSIX test is newly skipped or weakened, and the
      POSIX supervisor behavior is unchanged. The only POSIX restructuring
      is the shared admission-helper extraction in §2; preserve its callback,
      compensation, interrupt and pipe-write semantics.
- [ ] **Docs** (canonical and packaged twins in sync, `tests/test_packaging.py`
      green):
      - `coga/install` lists native Windows as supported and adds a
        Windows baseline (see *Proposed shape* §9).
      - `coga-dev/internals/agent-spawn` describes the Windows supervisor.
      - `coga-dev/internals/launch-claims` describes both pipe and named-event
        admission without changing the transaction.
      - `coga-dev/internals/activity-capture` accounts for Windows DWORD exit
        codes and the batch pointer's existing exact-line marker matching.
      - `coga/launch` notes the Windows idle-timeout refusal under
        *Options and exits*.
      - `coga-dev/codebase` lists the new module.
      - `coga/testing/clean-install/windows-aws` describes the attended
        `ssh -tt` check, retaining RDP as a fallback.
      - The README sentence "Coga runs on Linux, Windows or macOS…"
        stays true, unedited.
- [ ] **Teardown.** Every box is torn down, `status` confirms nothing is
      billing, and the PR reports the instance, AMI, zone and teardown
      time per the `windows-aws` runbook.
- [ ] **Human check.** After the PR is open and before merge, Zach installs
      the PR's wheel on his own Windows machine by following
      `v1/29-test-and-fix-install-on-macos-and-windows`'s
      guide. He walks install, then `coga init`, then a first `coga ticket`.
      The owner's `review` step tracks his findings, and blocking ones are
      fixed before merge. The handoff includes the exact PR-wheel install
      command and source commit; update the guide's PyPI-only instruction
      and old expected `fcntl` stop for this check.

### Proposed shape

1. **The platform split stays behind `run_with_done_marker`.** Its
   signature, `ReplOutcome`, `emit_done_marker`, `_sentinel_signals_done`,
   and the sentinel protocol stay unchanged. At the top of
   `src/coga/repl_supervisor.py` `run_with_done_marker()`, branch with
   `if os.name == "nt": return repl_supervisor_nt.run(...)`, passing every
   argument through. Do it after the existing argument validation. The
   POSIX body below changes only for the admission-helper extraction in
   §2. The supervisor entry and outcome contracts stay shared.
2. **New module `src/coga/repl_supervisor_nt.py`.** It is the Windows
   backend and is imported lazily, so POSIX never loads it. It is
   core infra by the microkernel rule, because it is half of the shared
   supervisor that every agent-spawn caller goes through. Its flow:
   - **Spawn.** The child inherits stdin/stdout/stderr (no PTY, no proxy)
     and the complete `env` plus `SENTINEL_ENV`, the same as POSIX. Start
     it through `oscompat.ProcessTree` (the Job Object with
     `KILL_ON_JOB_CLOSE` and the join-the-job wrapper from the core
     ticket) with `CREATE_NEW_PROCESS_GROUP`. Resolve `cmd[0]` with
     an explicit search of the supplied child environment's PATH and
     PATHEXT, rather than accidentally searching the parent's environment.
     Carry the resolved absolute executable into the command plan in §5
     and the wrapper; do not resolve it a second time using ambient state.
     A missing binary raises `AgentCliNotFound(cmd[0])`, matching the
     non-TTY branch.
   - **Held-child gate.** When `after_spawn` is given, the wrapper joins
     the Job and then waits on a per-spawn named event
     (`Local\coga-gate-<uuid>`) before it runs `cmd`. The parent runs
     `release_gated_child`'s logic, with `spawn_release_guard`,
     `after_spawn`, `after_spawn_release` and `on_spawn_admission_failure`
     in the same order and with the same failure semantics. `SetEvent`
     replaces the one-byte pipe write as the commit point. Failure
     before release terminates the Job, which kills the held wrapper, and
     re-raises. Lift that admission sequence out of the POSIX function
     into a shared private helper parameterized by a `release()`
     callable, rather than copying it. The probe proved this gate on the
     box. Test all four failure boundaries: before release, failed
     `SetEvent`, failure after successful release, and failed compensation
     while the release guard is held. After release, retain the admission
     effects even if a later callback fails, as on POSIX.
   - **Wrapper.** The wrapper sets `SIGINT` and `SIGBREAK` to `SIG_IGN`
     before it waits, so a CTRL_BREAK stops the agent while the wrapper
     survives to propagate the agent's real exit code. Without this,
     Python's default CTRL_BREAK handling kills the wrapper first.
     Preserve the child DWORD losslessly: retain its unsigned value for
     classification, but pass its signed 32-bit equivalent to Python 3.11
     `SystemExit` (`code` below `0x80000000`, otherwise `code - 0x100000000`).
     Passing an unsigned NTSTATUS directly to `SystemExit` overflows
     Python 3.11's Windows C `long` conversion.
   - **Supervise.** Poll every `_SENTINEL_POLL_INTERVAL` with no `select`,
     and wait on the process with a timeout. Keep the same latching rules:
     `done_signalled` is latched even mid-teardown, and there is one
     last check after exit. Keep the same `max_session` trigger and the
     same `[coga watcher]` notices on stderr.
   - **Teardown** maps the POSIX grace escalation: `GenerateConsoleCtrlEvent
     (CTRL_BREAK_EVENT, wrapper_pid)` replaces SIGTERM to the group. After
     `_KILL_GRACE_SECONDS`, `TerminateJobObject` replaces SIGKILL. The
     notices name the Windows mechanism.
   - **Console state.** Before spawn, save `GetConsoleMode` for the
     stdin and stdout handles when they are consoles. On every exit path,
     restore them with `SetConsoleMode`. The probe showed Claude leaves
     stdin at mode 7 after it was 503. After a Coga-initiated teardown,
     write `_TTY_SANITIZE` to stdout as on POSIX. VT processing is on
     under ConPTY.
   - **Interrupts.** While the child runs, set the parent's
     `SIGINT`/`SIGBREAK` handlers to `SIG_IGN`, and restore them in
     `finally`. This mirrors POSIX, where raw mode turns Ctrl+C into a
     byte for the child. `_defer_spawn_release_interrupts` is already a
     no-op without `pthread_sigmask`, so keep it as is.
   - **Idle timeout.** If `idle_timeout` is not None, emit one
     `[coga watcher]` warning ("idle-timeout is unavailable on Windows;
     running with max-session only") and ignore it.
   - **Non-console stdout** (the POSIX `not sys.stdout.isatty()` branch):
     run the same Job/gate spawn and return `ReplOutcome(code, "natural")`.
     No sentinel channel, matching POSIX.
   - **Exit classification** gets a Windows twin of `_classify_exit`, built
     from a return code instead of a wait status:
     - Coga never stopped the child: the outcome is `natural` with the raw
       code.
     - Coga stopped it: report the teardown code (0 for `done`, 124 for
       `timeout`).
     - Exception: the code is an NTSTATUS error (`>= 0xC0000000`) other
       than `0xC000013A` (STATUS_CONTROL_C_EXIT) and the Job terminate
       code. Then the outcome is `crash` with that raw code. The notes
       mirror POSIX.
   - **Outer CLI exit.** Keep unsigned raw codes in `ReplOutcome`,
     `AgentSessionResult` and the launch service's result/error. Carry
     interactive-result provenance through `LaunchBail` as needed, and
     convert to the signed equivalent only when the CLI adapter raises
     its final exit for that Windows interactive result. This must cover
     both the result and exception routes through `commands/launch.py`;
     `cli.main` still runs normal cleanup and its eligible state sweep.
     Do not call `ExitProcess` early and bypass `finally`, or normalize
     every unrelated CLI exit. Installed `coga.exe` and
     `python -m coga.cli` must both preserve the DWORD as observed by a
     native parent process, not by SSH's narrower exit-status transport.
3. **`oscompat.ProcessTree` (core ticket) grows only what the supervisor
   needs**: an optional held-start gate, an optional new process group,
   and a graceful `interrupt()` (CTRL_BREAK on Windows) separate from
   `kill()`. Existing consumers (`recurring_clone`, `recurring_runner`)
   keep their current calls and behavior, including their existing wrapper
   exit policy: the interactive wrapper mode opts into the signal and
   lossless-exit behavior in §2. Keep the wrapper short. It
   counts against the Windows command-line budget in §5, so if it is a
   `-c` string, keep it to a few hundred characters, or move it to a
   tiny importable module run as `python -m`.
4. **`coga launch --idle-timeout` refusal.** In
   `src/coga/commands/launch.py`, when `os.name == "nt"` and
   `idle_timeout is not None`, set `git.state_sweep_withheld` and exit 2
   before calling the launch service. Reuse the core port's refusal
   mechanism if its merged implementation supplies an equivalent.
   `cli.main` must honor the flag on its `SystemExit` path without
   changing this refusal to exit 75 or suppressing ordinary exit-2 sweeps.
   The message names the limitation and suggests `--max-session`; any
   sweep-withheld diagnostic must accurately describe this option refusal.
   Test through `cli.main`, with a remote and dirty Coga state, asserting
   unchanged file bytes, index, branch, local HEAD and remote tip. Direct
   `CliRunner.invoke(app, ...)` coverage is not enough. Python callers are
   not refused (§2 warns instead).
5. **Prompt and command delivery on Windows.** POSIX keeps
   `_argv_prompt()`'s existing `_MAX_PROMPT_ARG_BYTES` rule. Windows
   chooses between the complete prompt and its file pointer by planning
   the complete command, after `build_agent_command` and the kickoff:
   - For a native executable, build the final argv with its resolved
     executable, launch flags, discussion-template tokens, title,
     session ID and kickoff. Serialize with `subprocess.list2cmdline`;
     count `len(serialized.encode("utf-16-le")) // 2 + 1`, including the
     terminating NUL. Require at most 32,767 UTF-16 units.
   - Independently serialize and bound the Python wrapper invocation.
     Reuse the actual wrapper-argv builder, not a guessed allowance.
     Reserve its job/gate identifiers before measuring, or use a proved
     worst-case serialized width for those fixed-format identifiers only;
     check the actual resulting wrapper line again before `CreateProcess`.
     A raw 24,000-character prompt threshold is not a correctness check.
   - If either native command line is too large, rebuild the complete
     command with the prompt-file pointer and repeat both checks. A
     resolved `.cmd`/`.bat` always starts with pointer form and also uses
     the lossless shell transport below. The full prompt stays byte-exact
     in its UTF-8 file for the whole session.
   - If pointer form still exceeds a limit, refuse before agent spawn,
     launch audit or spawn admission, with exit 2 naming the offending
     command line, measured size, limit and remedy (shorten configured
     launch/discussion arguments or use a native executable for a shim
     limit). Do not print sensitive argv values in that error. Reuse this
     planner at the callers' pre-activation/claim preflight, and withhold
     the final state sweep on refusal. Earlier completed script phases
     or sessions retain their existing state; no rollback of their work.
   - **Batch transport (owner choice, 2026-10-19).** Support shell-sensitive
     paths and arguments losslessly using one per-spawn environment
     variable containing the quoted command, rather than interpolating
     user values into shell source. Choose a fresh ASCII variable name
     (`COGA_BATCH_<uuid>`) without replacing an existing child variable.
     Its value is the resolved batch path followed by every final argv
     token, each always quoted: double embedded double quotes; double a
     run of backslashes immediately before those quotes or the closing
     quote; leave other backslashes and characters literal. This differs
     from CRT `list2cmdline` and needs its own serializer.
   - The interactive wrapper invokes an absolute Windows system
     `cmd.exe` with the **raw command-line string**
     `cmd.exe /d /e:on /v:off /s /c "%COGA_BATCH_<uuid>%"`, using the
     selected variable's real name. No `CALL`, extra shell, or
     `list2cmdline` pass over that shell source. AutoRun and delayed
     expansion are disabled. The command variable expands once, so
     percent sequences introduced by its value remain literal; quoted
     metacharacters remain data. Pass the transport variable in the child
     environment, without changing the parent's environment or writing
     an extra batch script. The optional interactive wrapper mode in §3
     distinguishes native argv from this shell plan; do not change the
     existing recurring/clone wrapper.
   - Bound both the literal shell invocation and its fully expanded
     command line at a conservative 8,191 UTF-16 units including NUL,
     and bound the outer Python wrapper at 32,767. A short variable
     reference does not waive the expanded-command or environment-value
     limit. Tests compare received argv and prompt-file bytes through
     direct and npm-style `%*` forwarders in both `.cmd` and `.bat` files,
     with special characters in the script path as well as arguments.
     The transport owns Coga's quoting; it cannot repair an agent shim
     that deliberately reparses or transforms its own arguments.
   - **Line breaks.** The Windows batch pointer separates its fixed
     prose and `coga-launch: <uuid>` with U+2028 LINE SEPARATOR, including
     a trailing separator. `usage._has_marker_line` already uses
     `str.splitlines()`, so the marker stays an exact standalone line
     without relaxing transcript matching. The full prompt file retains
     its original bytes and normal marker line; native executable and
     POSIX pointers keep their existing format. Test marker attribution
     and exclusion of pointer text from captured human content.
   - Raw CR or LF in any other final batch argument is refused with exit
     2 in the caller's preflight, with the sweep withheld and a remedy
     naming the argument's role (title, launch option, discussion token,
     or kickoff), not its potentially sensitive value. This narrow
     exception is owner-approved after the native probe showed truncation
     or loss of CR/LF; do not extend it to punctuation or valid paths.
     Validate before activation, authoring draft creation or queue
     admission; recheck the actual spawn command too. Initial refusal
     must not publish unrelated dirt. Native executable arguments retain
     their existing line-break support. Embedded NUL remains invalid at
     the OS process boundary on all paths.
6. **Megalaunch picker** (`src/coga/commands/megalaunch.py`). Replace
   `_read_key()` and the SIGWINCH self-pipe in `_pick_selection()` with a
   pair of platform functions behind the same "return one action string"
   contract. `_decode_key` and the `Live` rendering stay shared.
   - POSIX keeps today's code.
   - Windows uses `msvcrt.kbhit()`/`getwch()` in a 0.05 s poll loop. It
     returns `"resize"` when `shutil.get_terminal_size()` changes, because
     there is no SIGWINCH.
   - Map Windows keys to the POSIX byte forms before `_decode_key`. The
     box showed ↑ arrives as `"\xe0H"` and ↓ as `"\xe0P"` (map to
     `ESC [ A` / `ESC [ B`, and accept the `"\x00"` prefix too). Esc
     arrives as `"\x1b"`, Ctrl+C as `"\x03"`, Enter as `"\r"`.
   - For the entire Windows picker, from before the first render until
     confirmation/cancellation, install a SIGINT handler that sets a
     quit flag. A processed Ctrl+C can arrive as a signal between reads;
     the `"\x03"` key form and this flag both mean `"quit"`. Check the
     flag before reads, after each polling sleep and redraw, and before
     accepting Enter; cancellation wins over a queued confirmation.
     Restore previous handlers and console modes in `finally`, including
     setup/render errors. The handler does no rendering, saving or
     launching. Test native Ctrl+C during idle polling and during redraw;
     mocked `getwch -> "\x03"` is only key-decoder coverage.
7. **Remove the core ticket's refusal.** Delete
   `agent_sessions_supported()`/`_refuse_unsupported_platform()`, the
   message constant, and every call site the core ticket added (`launch.py`
   gates, `commands/ticket.py`, `commands/megalaunch.py`, `megalaunch.py`,
   `recurring_runner.py`'s Windows `agent_spawn_refusal`, and the
   `spawn_agent_session` backstop), along with their refusal tests.
8. **Tests.**
   - Delete `windows_interactive_skip` from `tests/conftest.py` and
     resolve each use.
   - Add `tests/test_repl_supervisor_nt.py` (Windows-only), using fake
     agents written with the core ticket's cross-platform stub helper. It
     covers:
     - the sentinel tears down a child whose grandchildren (`ping`,
       `cmd /c ping`) also die, with Job active count 0;
     - a child that ignores CTRL_BREAK is killed after the grace;
     - `max_session` gives 124/`timeout`;
     - natural exit passes ordinary nonzero and full DWORD codes through;
     - CTRL_BREAK and an NTSTATUS error cross the real interactive wrapper
       and outer CLI on Python 3.11, including a crash racing done;
     - the gate holds the child until release; the four failure boundaries
       in §2 preserve the guard, rollback and post-release retention rules;
     - the supplied complete environment reaches the child and executable
       resolution uses its PATH/PATHEXT even when the parent's differ;
     - console modes are restored;
     - `done_signalled` is latched after exit;
     - an idle-timeout warning is emitted.
   - Add Windows cases for the picker's key mapping and resize poll in
     `tests/test_megalaunch.py` (monkeypatch `msvcrt`), plus native
     signal-during-idle/redraw cases proving no selection is saved and no
     session starts. Require console/handler restoration on all exits.
   - Add the `cli.main` no-sweep refusal case from §4 and serialized
     command-budget tests from §5: quote/backslash-heavy prompts, non-BMP
     text, discussion templates, title/session/launch/kickoff arguments,
     both sides of each limit, and an oversized pointer-form command.
     Fake native `.cmd`/`.bat` agents record their received argv and read
     the indicated prompt file; compare exact strings and file bytes,
     including shell-sensitive paths, rather than merely asserting that
     a pointer was selected. Include raw-CR/LF refusal without lifecycle,
     audit or sweep effects, plus the U+2028 pointer's existing exact-line
     usage matching. Retain ordinary POSIX marker tests unchanged.
   - The box run for the first acceptance item is a manual, recorded
     check, not a pytest. Drive it from a host-side PTY, as the
     blackboard's probe did, and record it in the PR.
9. **Docs.** Update `docs/contexts/coga/install/SKILL.md` and its packaged
   twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md`.
   Replace the "Linux or macOS (POSIX). Native Windows is unsupported"
   bullet with Linux, macOS, or native Windows, stating Windows Server
   2025 as the tested version (owner, 2026-10-19), and add a short *Windows baseline* subsection covering:
   - Python 3.11+ through uv (`irm https://astral.sh/uv/install.ps1 | iex`,
     then `uv python install 3.11`);
   - `%USERPROFILE%\.local\bin` on PATH after `uv tool install`, with
     `uv tool update-shell` and a new terminal;
   - Git for Windows (its installer's default `core.autocrlf=true` is
     fine, since Coga writes LF and Git normalizes);
   - PowerShell, for example in Windows Terminal (Coga needs no bash);
   - agent CLIs: Claude Code's native installer is the tested agent;
     Codex is untested on native Windows;
   - the `--idle-timeout` limitation.
   Also update `coga-dev/internals/agent-spawn` (*The supervisor* and
   *Large prompts*: serialized budgets and batch transport),
   `coga/launch` (*Options and exits*: the Windows idle-timeout and
   unrepresentable-command refusals),
   `coga-dev/internals/launch-claims` (*Held child and admission*: pipe versus
   named event), `coga-dev/internals/activity-capture` (Windows exit-code
   representation and batch-pointer marker matching), `coga-dev/codebase`
   (the new module), and
   `coga/testing/clean-install/windows-aws` (SSH attended check with RDP
   fallback). Check each one's packaged twin. Update
   `coga/tasks/marketing/fix-installer/test-and-fix-install-on-macos-and-windows/guide-for-zach.md`
   with the exact PR-wheel install instruction and remove the obsolete
   expected `fcntl` stop for that walk. The PR supplies the wheel location,
   source commit and digest; use
   `uv tool install --force --python 3.11 <the-downloaded-PR-wheel.whl>`,
   with the real filename filled in, rather than a PyPI release.

### Out of scope

- A ConPTY/pywinpty backend, or measuring idle-timeout on Windows by any
  heuristic (Job CPU time, I/O counters). Revisit only with a new ticket.
- Verifying Codex on native Windows. This ticket tests Coga, not agent
  CLIs (owner, 2026-10-19). The `.cmd` prompt-pointer rule stays, because
  it is Coga's own behavior.
- WSL, macOS changes, and CI (`windows-native/02-pr-ci-with-linux-and-windows-test-jobs`).
- Changing recurring/clone `ProcessTree` behavior on Windows. Those
  consumers keep hard-kill semantics.
- Editing the README. Its platform sentence already says Windows.
- What `coga init` seeds into user repos' `.gitattributes` (the core
  ticket's open question).

## Context

- `src/coga/repl_supervisor.py`:
  - `run_with_done_marker()` is the single supervisor entry, called only
    from `src/coga/launch.py` `spawn_agent_session()`. Its POSIX body has
    three regions: the non-TTY fork-gated branch, the `pty.fork()` branch,
    and the select loop with `_trigger_term()`. `release_gated_child()` is
    a closure inside it, holding the admission sequence that §2 lifts out.
  - `_classify_exit()` maps a `waitpid` status, so it cannot take a
    Windows return code; hence the Windows twin.
  - `_KILL_GRACE_SECONDS` (2.0), `_SENTINEL_POLL_INTERVAL` (0.25),
    `_TIMEOUT_EXIT_CODE` (124) and `_TTY_SANITIZE` are module constants
    the Windows backend reuses.
- `src/coga/launch.py`:
  - `_argv_prompt()` and `_MAX_PROMPT_ARG_BYTES` decide pointer vs
    verbatim prompt.
  - `build_agent_command()` builds argv.
  - `spawn_agent_session()` passes `idle_timeout`/`max_session` and the
    gate callbacks (`admit_spawned_child`, `rollback_spawn_admission`,
    `git.state_lock` as the release guard) into `run_with_done_marker`.
- `src/coga/commands/launch.py`: the Typer `--idle-timeout` /
  `--max-session` options.
- `src/coga/cli.py`: `main` and `_sweep_coga_state` own the final sweep;
  `git.state_sweep_withheld` prevents a refusal from publishing dirty state
  while preserving its exit code.
- `src/coga/usage.py`: `_has_marker_line` matches exact stripped lines
  from `str.splitlines()`, which already recognizes U+2028. Preserve the
  message-role filters and exact-match rule; only batch-pointer formatting
  changes.
- `src/coga/recurring_runner.py`: `_recurring_idle_timeout()` (900 s
  default, `COGA_REPL_IDLE_TIMEOUT`, `[launch].idle_timeout`) and
  `_recurring_max_session()` feed unattended sessions. `src/coga/megalaunch.py`
  imports both. These are the Python callers that get the warning, not a
  refusal.
- `src/coga/commands/megalaunch.py`: `_read_key()`, `_decode_key()` and
  `_pick_selection()` (the SIGWINCH self-pipe plus `signal.set_wakeup_fd`).
- `src/coga/recurring_clone.py`: `_WindowsJob` and `_WINDOWS_JOB_WRAPPER`
  are the Job Object code that the core ticket moves into
  `oscompat.ProcessTree`.
- Contract topics the Windows path must honor: `coga/launch` (*The step
  chain*, *Options and exits*) and `coga-dev/internals/agent-spawn` (*The
  supervisor*: sentinel content match, 0.25 s poll, 2 s grace, `ReplOutcome`
  kinds, `done_signalled`, terminal reset).
- Harness: `scripts/clean-install/aws-windows.sh` (`provision`, `checkout`,
  `ssh`, `teardown`, `status`) per `coga/testing/clean-install/windows-aws`.
  `provision` cannot resume after an interrupted SSH wait. Rerun its tail
  steps (mkdir, scp `windows-walk.ps1`, `baseline`/`setup`/`baseline`) by
  hand, as this design session did.
- AWS: the `coga-test` profile, under the 2026-10-14 standing approval to
  provision and tear down after the owner's first OK (given), with
  teardown at the end of every session.

Previous ref: `windows-native/03-interactive-coga-launch-on-native-windows` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-14-interactive-coga-launch-on-native-windows-e8b518


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implement — phase 1 (2026-11-05, attended, Claude Opus 5.5)

**Scope split (owner, in session):** this session landed all code, Linux tests
and docs on the branch. **No bump.** The box acceptance loop (phase 2) runs in
a relaunch of this same `implement` step. At that point, ask the owner for the
API key per Open Question 1. The core ticket `windows-native/01` is merged, so
the prerequisite is met.

### Deltas from the spec (the landed core port's shape)

- The core port added more refusal sites than the spec lists:
  `require_agent_sessions()`, `_preflight_platform_target()` (launch entry and
  `_launch`), `_require_agent_after_script`'s Windows branch, and both
  `recurring_runner` sites (scan admission and paused-period resume). All are
  deleted, along with their tests and docs (`coga/launch` *Phases and routing*,
  `script-tickets`, `recurring/scheduling`, `tickets/authoring`,
  `checkouts/launch-boundary`, `first-task`, `current-direction`). The refusal
  used exit 75 (`RETRY_WITHOUT_SWEEP`). The idle-timeout refusal instead sets
  `git.state_sweep_withheld` and exits 2, as §4 requires. The sweep-withheld
  diagnostic in `cli._sweep_coga_state` now also covers "refused before
  changing state".
- `ProcessTree` had no gate, group or interrupt. It gained
  `interactive`/`gate`/`shell` (Windows-only) and `new_process_group`, plus
  `release()` and `interrupt()`. The interactive wrapper is the stdlib file
  `src/coga/_nt_session_wrapper.py`, run by path as `python -I` under the base
  interpreter. Base python has no `coga`, so `python -m` was not possible.
  The existing `-c` wrapper and the recurring/clone behavior are unchanged.
- Zach's guide: `v1/29` is done, and `guide-for-zach.md` now only points to the
  generic human-walk operator guide (`coga/skills/.../human-walk/operator-guide.md`).
  That guide has no PyPI-only instruction or `fcntl` stop to remove, so no
  guide edit was needed. The exact PR-wheel command
  (`uv tool install --force --python 3.11 <wheel>`) plus the source commit and
  digest belong in the PR/handoff for the human check.
- README (owner, in session): the "Native Windows is not ready" paragraph is
  replaced with a pointer to `coga/install#windows-baseline`. The platform
  sentence is unedited.

### Decisions made while implementing

- `classify_exit` treats an NTSTATUS error (≥0xC0000000, except 0xC000013A) as
  `crash` even when Coga never stopped the child. This mirrors POSIX, where an
  untouched signal death is a crash. Full DWORDs below that range are
  `natural` with the raw code.
- The DWORD→signed conversion is `oscompat.process_exit_status`, applied only in
  the `commands/launch.py` adapter (both LaunchBail and result routes) and
  `commands/ticket.py`'s agent exit. It only changes values ≥2^31 on Windows,
  so no other CLI exit is affected.
- Planner: `repl_supervisor_nt.plan_agent_command` (pure, importable on POSIX).
  Launch calls it via `launch._plan_windows_agent_command`, using
  `_agent_command_parts` for role tags. Preflight is `agent_command_refusal`
  (pointer form, fixed-width placeholders). Call sites: launch
  `_prepare_agent` (after secrets, before push-auth and lifecycle writes),
  `coga ticket` (new `before_create` hook on `_resolve_or_create_target`,
  which also moves `--pick-agent` before draft creation for new drafts), and
  megalaunch `_preflight_agent_launch` (per-ticket failure, no global sweep
  withhold). Spawn-time refusal raises `AgentCommandRefused` (a
  `ComposeError`, which every caller already catches) and withholds the sweep.
- Watcher notices on Windows go to stderr (spec §2) in ASCII.
- Picker: `_PosixKeys`/`_WindowsKeys` key sources share `_decode_key`.
  Windows installs a quit-flag SIGINT handler and saves/restores console modes
  for the whole picker. Cancellation is checked after each read and redraw,
  and wins over Enter.

### POSIX-only tests kept under `windows_skip` (each names its Windows equivalent)

`tests/test_repl_supervisor.py`: all 31 former `windows_interactive_skip`
cases (`_classify_exit` ×4, no-TTY fork gate ×8, PTY loop ×19). Their Windows
equivalents are in `tests/test_repl_supervisor_nt.py`.
`tests/test_ticket.py::test_ticket_cancellation_pty_finalizes_sibling_or_reports_retained_state`
(pty.fork + group SIGTERM fixture). `tests/test_megalaunch.py::test_read_key_resize_beats_pending_keypress`
(raw PTY/SIGWINCH), whose equivalent is `test_windows_keys_resize_and_extended_keys`.
These now run on Windows unskipped: the 7 megalaunch picker CLI tests (they
patch the key-source `read`), `test_launch_functionally_auto_restarts_through_three_steps`
(fake agent via `write_executable`, a `.cmd` on Windows, which also exercises
the batch transport), and `test_second_chat_cannot_switch_an_active_chats_clean_feature_checkout`.
None of these have run on Windows yet; that is phase 2.

### Phase 2 checklist (box, next session)

1. Provision; `checkout` the branch; run the full native suite (long-run
   scheduled-task recipe in `windows-aws`). Fix failures, especially the 21
   `windows_only` cases in `test_repl_supervisor_nt.py`, the picker signal
   tests, the batch round-trip and the outer-CLI DWORD cases.
2. Attended `ssh -tt` acceptance driven from a host PTY (pyte): bump to an
   owner step, mark done, block, a two-agent-step chain, `--max-session`,
   `--idle-timeout` exit 2 with no sweep, Ctrl+C as input, closing SSH
   mid-session, and the megalaunch picker keys/resize/Ctrl+C. Each check needs
   Job count 0, no `claude.exe`/node/bash left, and console modes equal.
   Also check `coga.exe` and `python -m coga.cli` DWORD exits seen by a
   native parent.
3. Teardown + `status`; record instance/AMI/zone/teardown time here.
4. Then the PR-preparation record (`## PR`), and bump.

## Implement — phase 2, session 1 (2026-11-05/06, attended, Claude Opus 5.5)

**Paused by the owner ("tomorrow"). No bump.** Relaunch this `implement`
step to continue.

### Done this session

- Linux full suite on phase-1 HEAD: **4512 passed, 31 skipped** (Python
  3.12 `.venv`, `python -m pytest -q`).
- Box `win-launch2`: i-0c10cad7c9881160f, us-east-1a, t3.large, AMI
  ami-0b5f645abc199e666 (`Windows_Server-2025-English-Full-Base-2026.10.28`),
  build 26100.33674, Git 2.56.0.windows.4, uv 0.13.7, Python 3.11.18,
  Claude Code 2.1.318 (native installer). Launched 2026-11-06T05:02:44Z,
  **terminated 05:38:10Z**, SG deleted 05:38:11Z, key pair 05:38:12Z;
  `status` showed `terminated`, with no volumes.
- Native results on the branch (via harness `ssh`):
  - `tests/test_repl_supervisor_nt.py`: at first 72 passed and 4 failed. All 4
    batch round-trip cases (`direct`/`npm` × `.cmd`/`.bat`) printed
    `?\ was unexpected at this time`. The cause was the **fake shims**,
    which re-parsed their own directory: the direct shim embedded the literal
    UTF-8 path (`%PATH%`, `&`, `東`) in batch source, and the npm shape
    uses cmd-shim's unquoted `SET dp0=%~dp0`, which splits on `&`. The
    transport itself was fine. Fix (2814a2f13): the direct shim uses quoted
    `%~dp0` and keeps the full adversarial directory; the npm-shaped dir
    omits only `&`/`^`, which real npm shims can't survive (spec §5: the
    transport cannot repair a shim that reparses). After the fix: **76 passed, 1
    skipped** (the skip is "no console attached" under non-tty ssh, so it is
    to be covered by the attended run).
  - `tests/test_megalaunch.py`: there were 9 failures. Eight were "agent CLI 'claude'
    not found": the tests fake `shutil.which` and the supervisor, but
    the Windows planner resolves against the child PATH/PATHEXT first.
    Fix (c67dfc978): a Windows-only autouse fixture in `tests/conftest.py`
    (`_windows_agent_resolution_follows_which`) tries the real resolver
    and then falls back to `shutil.which`. It excludes
    `test_repl_supervisor_nt.py`, which owns the real resolver contract.
    The ninth, `test_megalaunch_cli_picker_resize_keeps_state`, used
    `signal.SIGWINCH`; it now checks SIGINT on Windows (the quit-flag
    handler). After the fix: **141 passed, 1 skipped**.
  - `test_usage.py` and `test_cli.py` had no failures in the first combined run.
  - The full native suite started as an S4U scheduled task and was **stopped
    at 7% with no failures** when the owner paused. It needs a complete
    rerun. Recipe: the inner pytest command is base64-encoded into a
    `powershell -EncodedCommand` task action, writing `stdout.txt`,
    `stderr.txt`, `junit.xml` and `exit.txt` under
    `C:\coga-clean-install\suite\`. Copy the registration `.ps1` over
    with `scp` (the harness's key/known_hosts in
    `.coga/clean-install/<name>/`). Passing it through `aws-windows.sh ssh`
    as an encoded command hits "The command line is too long."
- Claude Code + coga were installed on the box (`uv tool install --force
  --python 3.11 C:\Users\Administrator\coga-work`), but no auth yet.

### Next session

1. **First, ask the owner for Claude auth.** Either an `op://` reference
   for the API key (piped over SSH stdin into the session env only), or
   the owner runs `claude` login over `ssh -tt` (SSO). The `coga-test` AWS
   SSO session may also need `aws sso login --profile coga-test`.
2. Provision, `checkout`, start the full native suite task, and install Claude
   Code + coga.
3. Throwaway repo on the box: `brief-for-human` gives agent→owner for the
   bump case. For the chain, add a local two-agent-step workflow. Pin
   `launch_args = "--model haiku"` in the box's `coga.local.toml`.
   The host PTY driver needs `uv run --with pyte` (pyte isn't installed).
4. Continue the phase 2 checklist above from item 2.

## Design session 2026-10-19 (design step)

The core ticket was still at `review-design` (not merged). The owner chose
to design now against its spec and gather box evidence with standalone
probes. The implement step must wait for the core ticket's merge and adapt
to its landed `oscompat` shape.

### Box probe record

- Box `win-launch1`: i-0010c9788e70b0615, us-east-1a, t3.large, AMI
  ami-0b16ced290e00a1a3 (Windows_Server-2025-English-Full-Base-2026.10.14),
  build 26100.33650, Git 2.56.0.windows.2, uv 0.13.2, Python 3.11.17,
  Claude Code 2.1.304 (native installer, `~\.local\bin\claude.exe`),
  pywinpty 3.1.0. Launched 22:07:52Z. **Torn down** about 22:21Z; `status`
  showed `terminated`, with no volume, security group or key pair left.
- The first `provision` run was interrupted during the SSH wait. Its tail
  steps were rerun by hand (see `## Context`).
- Method: host-side `pty.fork` running `ssh -tt …`, with keystrokes sent on
  a timer and the screen rendered with `pyte` (120x40). The sentinel was
  written from a second ssh connection. Probe scripts were in the session
  scratchpad: `drive.py` (host) and `winsup.py`/`fake.py`/`keys.py` (box).
  They are not committed. Recreate them from this description if needed.
- **P1, claude directly over `ssh -tt`: PASS.** The onboarding TUI rendered
  fully, ↓ moved the theme cursor, and Enter advanced to the login-method
  screen. The SSH TUI path works, so the RDP fallback is not needed for
  acceptance 1.
- **P2, inherited console plus Job Object plus named-event gate: PASS.**
  - Job active processes were 1 (wrapper) while the gate was held. With a
    fake agent the tree reached 6 processes (a python child spawning `ping`
    and `cmd /c ping`), and 0 after either teardown.
  - With `TerminateJobObject` the exit code was 0xC000013A and teardown
    took about 0.25 s.
  - With `CTRL_BREAK_EVENT` to the `CREATE_NEW_PROCESS_GROUP` wrapper,
    claude exited on its own in about 0.25 s, and the grace kill never
    fired. On break it emitted some of its own cleanup (`\x1b[>4m`, title
    reset).
  - Claude left the console stdin mode at 7 when it had been 503, so
    save/restore is required. After restore the modes matched (503, 7).
  - In the probe the wrapper did *not* ignore CTRL_BREAK, so the
    wrapper's exit code was 0xC000013A. The spec therefore makes the
    wrapper ignore it.
- **P3, pywinpty ConPTY proxy: works, but worse.** The TUI rendered and
  input worked (with stdin set to raw VT input mode 0x200). CTRL_BREAK did
  *not* reach claude inside the inner ConPTY, so every teardown hit the 2 s
  grace and then `TerminateJobObject`. `PtyProcess.spawn` shlex-splits a
  string argv (`posix=False`) and crashed on the quoted wrapper; a list
  argv works.
- **P4, `msvcrt.getwch` over `ssh -tt`: PASS.** ↑ arrived as `'\xe0H'`, ↓
  as `'\xe0P'`, Space as `' '`, Enter as `'\r'`, Esc as `'\x1b'`, and
  Ctrl+C as `'\x03'`, a key rather than a signal.
  `shutil.get_terminal_size()` returned 120x40.

### Decisions (owner, 2026-10-19, in session)

- Proceed with the design before the core ticket merges, gathering
  evidence with standalone box probes.
- The Windows supervisor uses an **inherited console**, not pywinpty.
- `--idle-timeout` on Windows: the **explicit flag refuses (exit 2)**;
  Python callers that arm it get a warning and run with max-session only.
  No heuristic.

### Findings the design leans on (not from the box)

- `CreateProcess` caps the whole command line at 32,767 UTF-16 units,
  well below Linux's 128 KiB-per-argument limit that
  `_MAX_PROMPT_ARG_BYTES` targets. Composed prompts often exceed that, so
  the pointer path is routine on Windows.
- npm-installed CLIs are `.cmd` shims. Running one goes through `cmd.exe`
  (8,191-character limit, `%`/`^`/`&` expansion), so those CLIs always get
  the pointer.

## Open Questions

1. **Answered (owner, 2026-10-19): (b), an API key.**
   - At implement time, ask the owner for the key in the attended
     session. Pass it to the box over stdin into the session env only:
     never in the repo, a ticket, a log, a command line, or a file
     outside the box.
   - Pin the throwaway test repo's agent to Haiku with
     `launch_args = "--model haiku"` in the *box's* `coga.local.toml`.
     That file is box-only and never committed.
   - Use a trivial test ticket whose session runs only the lifecycle
     command under test.
   - Expected spend: about 25 sessions at roughly $0.01 each on
     Haiku 5.5.
   - The owner checks the credit balance in the Console
     (Settings → Billing).

   Original question: **Claude Code auth on the throwaway box** (acceptance 1 needs a logged-in
   agent). Options:
   - (a) The owner runs `claude` login on the box over `ssh -t` once per
     box, through the device/URL flow.
   - (b) The agent pipes an `ANTHROPIC_API_KEY` from the owner's local
     secret store over stdin into the session env, never onto disk in
     the repo or onto a command line.
   - (c) `claude setup-token`, with its output delivered the same way.

   Which should the implement step use? The repo is public, so nothing can
   be written into logs or tickets.
2. **Answered (owner, 2026-10-19): state Server 2025 as the tested
   version.** The spec's §9 is updated. Original question: **The
   supported-version floor stated in `coga/install`.** Only Server
   2025 was tested, plus Zach's machine at the human check (presumably
   Windows 11). Inherited-console TUIs need ConPTY/VT, which arrived in
   Windows 10 1809. Should the doc state "Windows 10 1809+ / 11 / Server
   2022+", or only "Windows 11 and Server 2025 (tested)"?
3. **Answered (owner, 2026-10-19): no Codex run. We test Coga, not the
   agent CLIs.** `coga/install` says Codex is untested on native Windows.
   Original question: **Codex on native Windows.** The spec only guarantees that a `.cmd`
   shim gets the prompt pointer. Should `coga/install` say "Codex
   untested on native Windows", or should a Codex run on the box be added
   to acceptance?
4. **Answered (owner, review-design, 2026-10-19): support shell-sensitive
   paths and arguments losslessly.** The owner chose the additional
   transport work and native tests over refusing these configurations.
   This concerns fake `.cmd`/`.bat` agents and Coga's argv delivery;
   it does not add a Codex acceptance run.
5. **Answered (owner, review-design, 2026-10-19): reject raw CR/LF only
   in batch-agent arguments.** The native probe showed those bytes are
   lost or truncate the command, while punctuation/path support succeeds.
   Keep full multiline prompts byte-exact in the file and use Unicode
   line separators in the generated batch pointer. Refuse affected
   configured arguments in preflight with a clear remedy.

## Evaluator review

2026-10-19 — **Needs corrections before implementation.** Reviewed the
Description and Context as the implementer's contract before consulting the
design notes, then checked current source, tests, fixtures, owning topics and
the packaged workflow. Reconciled clean main through `d34aeec10`, including
the owner's newly answered API-key question. The body headings compose
correctly, the owner gate fits the work, and the platform backend belongs in
the shared spawn infrastructure. The core-port ticket remains at
`review-design`; `oscompat.ProcessTree`, the refusal helper and the skip
marker have not landed. That is the stated prerequisite, not an omission in
this implementation.

### Must fix before implementation

1. **P1 — An exit-2 idle-timeout refusal still publishes state.** Proposed
   shape §4 stops before the launch service, but `src/coga/cli.py`
   `main` calls `_sweep_coga_state` on ordinary `SystemExit`, including
   2; `_should_sweep_coga_state` includes `launch`. Dirty ticket/log/context
   edits can therefore be committed and pushed despite acceptance's
   "before any state change" promise. Specify how this refusal withholds
   that final sweep while retaining exit 2, using the core port's mechanism
   if it introduces one. Test through `cli.main`, with dirty Coga state
   and a Git remote, asserting unchanged files, index, local HEAD and remote
   tip. `CliRunner.invoke(app, ...)` alone misses this boundary.
   Existing evidence: `tests/test_cli.py`
   `test_inherited_assist_still_sweeps_cli_state` and
   `test_withheld_launch_return_skips_the_sweep_and_keeps_the_exit`.

2. **P1 — Preserve the agent's full Windows exit code through the wrapper.**
   The reused `src/coga/recurring_clone.py` `_WINDOWS_JOB_WRAPPER` ends
   with `raise SystemExit(subprocess.call(...))`. Adding ignored
   SIGINT/SIGBREAK alone does not preserve NTSTATUS codes on the Python 3.11
   floor: CPython's `_Py_HandleSystemExit` converts with
   `PyLong_AsLong`, and Windows `long` is signed 32-bit. From those
   sources, an unsigned status such as `0xC000013A` or `0xC0000005`
   overflows to -1 (observed by a Windows parent as `0xFFFFFFFF`).
   The proposed classifier would then misidentify a normal CTRL_BREAK
   termination as a crash, or lose the real crash code. Specify lossless
   32-bit propagation in the interactive wrapper and at the outer CLI
   process exit, without silently changing the deferred recurring/clone
   contract. Require native Python 3.11 end-to-end cases for ordinary
   nonzero exit, CTRL_BREAK, and a real NTSTATUS error, including a crash
   racing a done signal; classifier-only tests cannot catch the wrapper.
   This is a source-derived finding, not a new box observation.
   Sources: [CPython 3.11 SystemExit handling](https://github.com/python/cpython/blob/v3.11.17/Python/pythonrun.c#L653-L715),
   [Microsoft integer ranges](https://learn.microsoft.com/en-us/cpp/cpp/data-type-ranges?view=msvc-170).

3. **P1 — Make the prompt budget a check of the serialized command lines.**
   §5 recognizes quoting but then prescribes approximately 24,000 UTF-16
   units for the prompt, without defining the counting point or handling
   oversized non-prompt arguments. A local serialization probe with
   `prompt = '"' * 23_000` produces **46,011** UTF-16 units for
   `subprocess.list2cmdline(["claude.exe", prompt])`, already beyond
   CreateProcess before the wrapper. `launch._argv_prompt` currently runs
   before `build_agent_command`, which adds discussion-template tokens,
   launch flags, title and session ID. Specify a bound on the final quoted
   agent argv and the wrapper argv, including the terminating NUL; rebuild
   with the pointer when needed and define an actionable failure if the
   remaining argv still cannot fit. Add quote/backslash-heavy, non-BMP,
   discussion-template and boundary cases.
   Source: [CreateProcessW command-line contract](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).

4. **P2 — A short pointer is not yet a defined .cmd/.bat transport.**
   §5 asks for a pointer containing no cmd metacharacters, but
   `compose.write_prompt_file` uses the user's temp directory, and
   `launch._argv_prompt` interpolates that path and appends a multiline
   launch marker. A valid path containing literal `%PATH%` survives
   `list2cmdline` unchanged and is subject to shell expansion; other argv
   values from `build_agent_command` are not covered by checking only the
   pointer. Specify how such paths/arguments and the marker are transported,
   or explicitly refused before launch effects, and apply the 8,191 limit
   to the complete shim invocation. Test a native fake .cmd/.bat that
   records its received argv and reads the indicated file, including spaces,
   percent signs and other shell-sensitive characters. This tests Coga and
   does not require the excluded Codex run.
   Source: [Python subprocess batch-file parsing caveat](https://docs.python.org/3.11/library/subprocess.html#security-considerations).

5. **P2 — Define Ctrl+C handling during the picker's polling intervals.**
   §6 assumes Ctrl+C will always be `"\x03"` from `getwch`. The
   existing POSIX `commands/megalaunch._read_key` deliberately enters raw
   mode; the proposed Windows `kbhit`/sleep loop has no equivalent
   whole-picker console-mode or signal policy. With
   `ENABLE_PROCESSED_INPUT`, Windows handles Ctrl+C as a signal instead
   of putting it in the input buffer. The recorded blocking-key probe does
   not establish behavior between reads in this polling loop. Specify
   either mode management with restoration or signal-to-quit handling that
   also covers idle polling/redraw, and test Ctrl+C in those intervals
   without saving a selection or launching anything. A mocked
   `getwch -> "\x03"` test alone cannot establish this contract.
   Sources: [Windows console input modes](https://learn.microsoft.com/en-us/windows/console/setconsolemode),
   [Python 3.11 console input](https://docs.python.org/3.11/library/msvcrt.html#console-i-o).

### Recommendations

- Make the Windows admission tests explicitly cover failure before release,
  failed `SetEvent`, failure after successful release, and compensation
  failure while the guard is held. Existing POSIX witnesses are
  `test_no_tty_spawn_release_guard_covers_callbacks_and_gate_write`,
  `test_no_tty_release_failure_compensates_before_reaping_held_child` and
  `test_no_tty_interrupt_after_gate_delivery_retains_admission`.
  Retain the complete-environment test too: resolve the executable against
  the supplied child environment, rather than accidentally using the
  parent's PATH. These are useful named entries in the required Windows
  replacement-test inventory.
- Extend the documentation checklist to
  `coga-dev/internals/launch-claims` ("Held child and admission", currently
  pipe-specific, local-only) and `coga/testing/clean-install/windows-aws`
  ("RDP", currently directing attended launch there), with the skill's
  packaged twin.
  Give Zach the exact PR-wheel install command: the cited
  `guide-for-zach.md` currently instructs a PyPI install and describes the
  old Windows fcntl stop. Correct the baseline cross-reference from §7 to §9.
- Clarify acceptance's "same" for lifecycle commands: bump advances one
  step, mark done ends the task, and block records a blocker; use separate
  disposable tickets. Keep the chain case separate from the one-step
  owner-handoff case. The owner's new auth/model/test-ticket directions
  resolve the earlier authentication question and must survive synthesis.

### Verification and limits

Read-only Linux checks, Python 3.12.12:

```sh
PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q \
  tests/test_cli.py::test_inherited_assist_still_sweeps_cli_state \
  tests/test_cli.py::test_withheld_launch_return_skips_the_sweep_and_keeps_the_exit \
  tests/test_cli.py::test_launch_entry_refusal_through_main_skips_the_sweep \
  tests/test_repl_supervisor.py::test_no_tty_spawn_release_guard_covers_callbacks_and_gate_write \
  tests/test_repl_supervisor.py::test_no_tty_release_failure_compensates_before_reaping_held_child \
  tests/test_repl_supervisor.py::test_no_tty_interrupt_after_gate_delivery_retains_admission \
  tests/test_launch.py::test_argv_prompt_pointer_repeats_launch_marker
```

Result: **11 passed**. Local Python probes confirmed the serialized length
above, literal percent expansion text/newlines in the existing pointer, and
that the idle-timeout launch argv is sweep-eligible. All six inspected topic
twins named above are currently byte-identical. No Windows instance was
provisioned, no new Windows execution evidence is claimed, and the full suites
remain implementation acceptance. Only this evaluator section was authored;
the ticket body, code and workflow remain for their owning steps.


Final checks: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.cli validate --task windows-native/03-interactive-coga-launch-on-native-windows --json` exited 0 (one task, no issues); `git diff --check` passed. The final `git fetch origin main` introduced no further changes.

## Review-design corrections — 2026-10-19

All five evaluator findings are accepted and addressed in the spec above:

1. §4 withholds the outer CLI sweep while keeping exit 2, with a
   `cli.main` test over dirty state and a remote.
2. §§2–3 preserve the interactive child's DWORD through both Python 3.11
   exit boundaries, without changing recurring/clone behavior. Native
   wrapper-plus-CLI tests must include CTRL_BREAK and a real crash racing
   done; classifier-only coverage is insufficient.
3. §5 measures the final serialized agent, wrapper and shell commands,
   rebuilds with the pointer, and defines preflight failure if that still
   cannot fit. No guessed prompt-only allowance remains.
4. §5 specifies a batch serializer and one-expansion environment
   transport, with native `.cmd`/`.bat` argument and file-content tests.
   The owner's lossless-punctuation choice and narrow raw-CR/LF exception
   are recorded in answers 4–5 above.
5. §6 handles Ctrl+C for the whole picker, including idle polling and
   redraw, and requires restoration and cancellation tests.

No finding was rejected. The admission-failure matrix, supplied-environment
resolution, lifecycle distinctions, documentation twins and Zach's exact
PR-wheel handoff recommendations are also incorporated. API-key delivery,
Haiku-only throwaway tickets, Server 2025 as the tested version and the
exclusion of a real Codex run remain as the owner decided.

### Native transport evidence

Standalone fake-agent probes on native Python 3.11.17; no repository
implementation or real-agent session was tested in this review:

- The selected whole-command environment transport passed **80/80**
  representable cases across `.cmd` and `.bat`, each with direct and
  npm-style `%*` forwarding. Exact argv and prompt-file hashes matched.
  Paths and arguments included spaces, percent sequences, exclamation
  marks, carets, shell operators, quotes, backslashes and Unicode. The
  injection-like input created no unexpected file.
- Raw LF, CR and CRLF failed all **12/12** selected-transport cases,
  motivating the owner-approved preflight exception. The broader
  four-transport comparison was 320/368; every failure was one of those
  line-break cases.
- A separate selected-transport stress run passed **184/184**, including
  deterministic mixed punctuation, empty arguments, long quote/backslash
  runs, non-BMP characters, Japanese paths and U+2028/U+2029. The batch
  pointer's exact standalone marker survived; full prompt bytes matched.
- A synthetic `ExitProcess` probe confirmed the Python 3.11 boundary:
  passing unsigned `0xC000013A` or `0xC0000005` to `SystemExit` produced
  `0xFFFFFFFF`; passing the signed equivalent preserved the original
  DWORD. Ordinary code 7 survived both forms. This proves exit transport,
  **not** real CTRL_BREAK, crash classification or Coga CLI acceptance.
- The transport's one-expansion premise agrees with Microsoft's
  [cmd variable-substitution contract](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmd).
  Local checking of the existing `usage._has_marker_line` confirmed
  U+2028 preserves exact-marker matching without changing its parser.

Local, ignored evidence is under
`.coga/clean-install/win-argv-review2-1019/`: `argv-review.py`,
`argv-stress.py`, their JSON results, `baseline.txt` and `host.txt`.
The scripts run with native `python.exe` through harness `ssh` and create
their fake agents in the box's temp directory. They are design probes,
not a replacement for the committed implementation tests in §8.

### Box receipt and remaining work

- Run `win-argv-review2-1019`: **i-0b4adfddaa3220e7a**, **us-east-1a**,
  t3.large, AMI **ami-0b16ced290e00a1a3**
  (`Windows_Server-2025-English-Full-Base-2026.10.14`), Server 2025
  build 26100.33650. Git 2.56.0.windows.2, uv 0.13.3, Python 3.11.17.
- Launched **2026-10-20T03:57:53Z**; harness teardown recorded termination
  at **2026-10-20T04:08:48Z**, security-group deletion at **04:08:50Z**
  and key-pair deletion at **04:08:51Z**. Final harness `status` confirmed
  `terminated`, no tagged volumes and no remaining security group or key.
- The first attempt, `win-argv-review-1019`, failed before allocation
  because sandbox permissions prevented an AWS SSO cache refresh.
  Its teardown and status also confirmed no resources. No API key or
  agent authentication was needed for either standalone probe.

Reconciled with main through `5adbea7a7`; intervening changes affected other
tickets, not this spec or its governing contracts. Only this ticket is
edited. The task remains at the owner's `review-design` gate; no workflow
transition is authorized by the transport-policy answers. The core-port
ticket is still at `review-design`, and implementation must wait for its
merge, then adapt to the landed `ProcessTree`. Full suites, actual
interactive launch acceptance and Zach's machine check remain future work.

Review validation: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python
-m coga.cli validate --task
windows-native/03-interactive-coga-launch-on-native-windows --json` exited 0
(one task, no issues); `git diff --check` passed. Local assertions confirmed
unchanged frontmatter, one blackboard fence, the required composable
Description subsections, and positive/negative exact-marker matching for
the U+2028 batch pointer.

## Swept live copies restored on main (2026-11-06)

A `Sync coga state` commit (421ee15c0) published this ticket's uncommitted
live-copy edits to main without their package owners. Branch
`fix/revert-swept-legacy-doc-copies` restores those live copies from the
package owners. Before or after merging, whichever lands second: copy each
changed package owner over its legacy live copy
(`docs/contexts/coga/{checkouts/launch-boundary,launch,recurring/scheduling,script-tickets,tickets/authoring}`
and `coga/skills/coga/testing/clean-install/windows-aws`) so
`tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`
passes.

## Implement — phase 2, session 2 (2026-11-06/07, attended, Claude Opus 5.5)

Done; bumped to open-pr.

- Rebased onto origin/main `ee4f104b4` (138 commits). The only conflict was
  `tests/test_launch.py`: kept main's new tests and dropped a stale
  `@windows_interactive_skip`. Fixed main's new gotcha in
  `docs/contexts/coga-dev/codebase/gotchas/SKILL.md`, which named the deleted
  `require_agent_sessions()`; it now names `launch.agent_command_refusal()`.
  Force-pushed as `a469b51f7`.
- Linux full suite on `a469b51f7`: **4562 passed, 31 skipped, 2 failed**.
  Both failures **pre-exist on origin/main** and are untouched by this branch:
  `test_live_and_packaged_copies_stay_identical` (`coga/skills/coga/releasing`
  live vs packaged drift) and `test_context_navigation_has_no_broken_links`
  (`coga-dev/testing` links a missing `macos-aws#full-suite-at-a-commit`
  anchor). Not fixed here (out of scope).
- Auth (owner): the owner logs in to their subscription on the box with `claude`
  over the harness `ssh`. No API key was used.
- Box `win-launch3`: i-05dc25bc97681ef1b, us-east-1a, t3.large, AMI
  ami-0b5f645abc199e666, build 26100.33674, Git 2.56.0.windows.4, uv 0.13.7,
  Python 3.11.18, Claude Code 2.1.319, coga 0.4.1 (branch checkout via
  `uv tool install`). Throwaway repo `C:\Users\Administrator\tt` with a bare
  local origin, a local `two-agent` workflow, and Haiku pinned in its
  `coga.local.toml`. Temporary Defender exclusions were added with owner OK;
  **remove and verify them before teardown**.
- Host driver: `pty.fork` + `ssh -tt` + pyte (`uv run --with pyte`). Box
  runner `run.py` ignores SIGINT/SIGBREAK, prints console modes before/after
  and the coga exit. A `.cmd` runner caught Ctrl+C itself ("Terminate batch
  job"), which is a harness artifact.
- Attended results so far (all PASS):
  - `--idle-timeout 30`: exit 2, limitation + `--max-session` message, sweep
    withheld. Staged/unstaged dirt, branch, HEAD, remote tip and file hash were
    unchanged, and the ticket stayed `active`.
  - `--max-session 20` (claude at onboarding): CTRL_BREAK at 20 s, child exit
    0x0, reported 124/`timeout`. No claude/node/bash left; modes 503/7 before =
    after. Noticed `coga usage: claude transcript not found:
    C:\Users\Administrator\tt\<id>.jsonl` because no session transcript existed
    yet; recheck the path once authenticated sessions run.
  - Picker: ↑/↓/j/k, Space, a/n, q, Esc pass. Resize redrew within 0.24 s,
    keeping the selection. Ctrl+C during idle polling and during redraw with a
    queued Enter both cancelled ("Nothing selected"): exit 0, no traceback, no
    saved selection, no session, modes restored.
- Real-agent attended results (owner logged in to their subscription on the box;
  Haiku pinned; folder trust pre-accepted in the box's `~/.claude.json`). All PASS.
  Every run: no claude/node/bash left in `tasklist`, and modes 503/7 before =
  after.
  - **bump** (`bump3`): the agent ran `coga bump`; sentinel trigger, CTRL_BREAK,
    child 0x0, exit 0; advanced exactly to step 2 `human-executes` (owner).
  - **mark done** (`done2`): the agent first asked (the step says "no live
    action"); I typed the authorization into the REPL, which also proves input
    works. Ticket `done`, exit 0. `done1` was the same refusal; its SSH was
    killed at the 300 s driver deadline with no orphans.
  - **block** (`block1`): `blocked`, reason "throwaway block check", exit 0.
  - **chain** (`chain1`, local `two-agent` workflow): two sessions in one
    launch, 1→2→3 `owner-check`, exit 0.
  - **Ctrl+C** (`ctrlc1`): Claude showed "Press Ctrl-C again to exit"; no
    KeyboardInterrupt/traceback; `--max-session 60` ended it, 124.
  - **SSH hang-up** (`hangup1`, killed at 40 s into a live session): no orphans.
  - **Picker Enter** (`COGA_REPL_MAX_SESSION=45 megalaunch --pick`, timeout2
    selected): launched only timeout2; exactly one `[coga watcher]
    idle-timeout is unavailable on Windows; running with max-session only`;
    the max-session teardown gave 124, so megalaunch reported 1 failed (exit 1).
  - **DWORD via a native parent** (fake `.cmd` agents through the batch
    transport): `coga.exe` and `python -m coga.cli` each returned 0xC0000005,
    0xC000013A and 7 exactly.
  - `bump1` ended natural exit 1 because my driver answered the trust dialog's
    default "No, exit" (a harness error); it shows natural exits pass through.
- Fixes found on the box (owner: fix here):
  - `59b43c47e` usage: Claude transcript dir naming now also maps `\` and `:`.
    On Windows usage was always "transcript not found" because the computed
    name was an absolute path. POSIX output is unchanged. Docs:
    `coga-dev/internals/activity-capture`.
  - `9b8a27e4b` checkout policy: compare step-skill twins with CRLF→LF, so a
    `core.autocrlf` checkout doesn't fall back to `manual`. Natively,
    `test_policy_checks_peer_review_skill_for_current_and_legacy_steps` ×3 had
    failed (from main, exposed by the box's CRLF checkout). Docs: `coga/checkouts`
    (both twins).
- The Defender process exclusions (`python.exe`, `git.exe`, `uv.exe`) were added
  by the owner (the classifier blocked my attempt). Remove these along with the
  path exclusions before teardown. The native suite was restarted on `9b8a27e4b`.
- First full native suite (S4U task, `9b8a27e4b`): **128 failed, 4367
  passed, 103 skipped, 3 h**. The owner said to fix everything, including the 25
  failures already on main. Causes and fixes:
  - **CRLF source checkout** (25 already on main: trim-log "custom clean
    filter", packaging pins, recurring carrier, edge-distribution timeouts).
    Git for Windows' `core.autocrlf=true` checked Coga out as CRLF. Fixtures
    copied CRLF templates, and safe-autocrlf kept them CRLF.
    `5a0e2d8b1`: repo-wide `* text=auto eol=lf` in `.gitattributes`; no
    committed bytes changed. Re-checkout: `git rm --cached -r -q . && git reset --hard`.
  - **Orchestration tests' fakes bypassed by the Windows spawn** (~95 in
    `test_launch`/`test_ticket`): they fake `shutil.which`/`subprocess.run`,
    so the planner resolved and ran the real installed `claude.exe`.
    `fd0083a37`/`a85bdf6a4`: a Windows conftest fixture. A faked `which` or
    `run` keeps the bare CLI name, and a faked `run` takes the no-console
    ungated spawn, as POSIX's no-TTY branch does. The real contract stays in
    `test_repl_supervisor_nt.py`.
  - **Detached Git maintenance held captured pipes**, which hung the trim-lock
    tests. `1027bf4b3`: `git._git_env` sets `gc.autoDetach`/
    `maintenance.autoDetach=false` on Windows. This is a production fix.
  - Smaller: usage tests' MAX_PATH (a shallow cwd on Windows), the
    `--idle-timeout` timeout test uses `--max-session` on Windows, LF
    fixture writes in trim-log/packaging tests, `test_git` ignores Windows'
    extra index-mode probe, the grandchild teardown test asks `tasklist`
    (`process_is_running` is conservative), and the trim-lock join is 60 s
    (a native trim takes about 12 s).
- Rebased again onto main `29df72447`. Main retired `coga/install`. The
  Windows baseline now lives in README *Get started* (also "Agent sessions run
  on Linux, macOS, or native Windows"), and first-task links there. Main
  restored legacy live copies per the note above; `8260f59f4` mirrors this
  branch's package edits into them. Main's new owner-filtered picker test lost
  its stale `windows_interactive_skip`.
- Linux full suite on the rebased head: **4717 passed, 33 skipped**, plus
  packaging/megalaunch reruns after the twin sync: 188 passed. Full native suite
  restarted on `8260f59f4`.
- Full native suite on `8260f59f4` (3 h 12 m): **33 failed, 4616 passed, 103
  skipped**. Causes and fixes (`b12825b33`, test-only):
  - 31 `test_launch` spawn tests fake `launch.run_with_done_marker`, but the
    Windows planner first resolved the CLI ("agent CLI 'codex' not found").
    The conftest fixture now keeps the bare name while that run is faked; the
    faked run never spawns, as on POSIX.
  - `test_installed_trim_log_adoption_and_headless_period[30-*]` (already on
    main): the installed-wheel launch with a real trim takes ~40 s natively, so
    `_run`'s bound is 120 s. `git log` is decoded as UTF-8, since the locale
    code page garbled the "—" subject. On the box: edge tests 14 passed, 7
    skipped; all 33 reran green.
- Main moved by state-only commits. I merged it (`8ab6297fc`; the force push
  of a rebase was refused), with no code change since `b12825b33`. Final
  native full suite started on `8ab6297fc`.
- Final native full suite on `8ab6297fc`: **4649 passed, 103 skipped, 0 failed**
  (3 h 18 m); Linux full suite on the same head: 4719 passed, 33 skipped.
- Cleanup: scheduled task `coga-suite` deleted; no python/git/uv/claude/node/bash
  processes left; all Defender path and process exclusions removed, and
  both lists were verified empty.
- Teardown 2026-11-08T03:29:53Z: `win-launch3` i-05dc25bc97681ef1b (AMI
  ami-0b5f645abc199e666, us-east-1a) terminated; SG and key pair deleted;
  `status` confirms terminated, no volumes; no other instances in us-east-1.
  The PR preparation record is below. Next: open-pr.

## PR

```yaml
title: Interactive coga launch on native Windows
author: claude
author_evidence: Implement phases 1 and 2 ran attended in Claude Code on Claude Opus 5.5; see the Implement sections on this blackboard.
head: 8ab6297fc1e2076fc0ffeebb6ecf09e1fd7c71c7
base: c00329d051a38dc4f320fc902d0d058703bc436a
depth: deep
rationale: >-
  New Windows process supervisor (console, Job Object, CTRL_BREAK teardown,
  batch transport) plus production fixes found on the box (usage transcript
  dir, CRLF step-skill compare, attached Git maintenance, repo-wide LF
  checkout). Platform-sensitive with no independent code review yet; inspect
  the diff.
implementation: >-
  coga launch, megalaunch and ticket-driven sessions run attended on native
  Windows through repl_supervisor_nt: an inherited console, a kill-on-close Job
  Object, CTRL_BREAK then sentinel teardown, max-session (124) timeouts, a
  .cmd/.bat prompt-pointer transport and DWORD exit codes preserved end to end.
  --idle-timeout is refused on Windows (exit 2, no sweep) and max-session is
  the bound. Usage capture finds Claude transcripts for Windows paths; checkout
  policy compares step skills with CRLF folded; Coga's own Git calls on
  Windows keep auto-maintenance attached so captured pipes are not held; the
  repo checks text out as LF everywhere. README Get started documents the
  native Windows baseline.
deviations: >-
  The owner extended scope during implement: fix the usage transcript path,
  the CRLF checkout-policy compare, and every native suite failure including
  the 25 already failing on main (CRLF checkout, timeouts). main retired
  coga/install, so the Windows baseline moved to README Get started. The
  final main reconcile is a merge (8ab6297fc) because the force push of a
  rebase was refused; it adds only coga state commits.
limitations: >-
  Tested on Windows Server 2025 24H2 with PowerShell 5.1, Git for Windows
  2.56 and Claude Code's native installer; Codex on native Windows is
  untested by owner decision. --idle-timeout is unavailable on Windows. The
  PyPI 0.4.1 wheel predates this; Zach can try the PR wheel with
  uv tool install --force --python 3.11 <wheel>. 103 tests skip natively,
  all POSIX-only mechanics (PTY/fork 32, bash clean-install harness 38,
  mode bits/permissions 11, process groups/signals 12, POSIX shell runbooks 7,
  AWS driver 1, no-console 1) with Windows counterparts in
  test_repl_supervisor_nt and the native installed-wheel tests.
files:
  .gitattributes: Check every text file out as LF so Git for Windows autocrlf cannot change fixtures or twins.
  README.md: Native Windows baseline in Get started; sessions run on Linux, macOS or native Windows.
  coga/skills/coga/testing/clean-install/windows-aws/SKILL.md: Legacy live twin of the package windows-aws skill edit.
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: LF checkout rule, attached Git maintenance on Windows, agent_command_refusal.
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: Claude transcript dir naming for Windows paths.
  docs/contexts/coga/checkouts/SKILL.md: Legacy live twin; CRLF step-skill checkout still equals its owner.
  docs/contexts/coga/checkouts/launch-boundary/SKILL.md: Legacy live twin of the Windows launch-boundary edit.
  docs/contexts/coga/first-task/SKILL.md: Legacy live twin; link to README native Windows notes.
  docs/contexts/coga/launch/SKILL.md: Legacy live twin of the Windows launch contract.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Legacy live twin of the Windows scheduling note.
  docs/contexts/coga/script-tickets/SKILL.md: Legacy live twin of the Windows script-ticket note.
  docs/contexts/coga/tickets/authoring/SKILL.md: Legacy live twin of the Windows authoring note.
  src/coga/_nt_session_wrapper.py: Windows session wrapper run inside the supervised console.
  src/coga/checkout_policy.py: Compare step-skill twins with CRLF folded to LF.
  src/coga/cli.py: Windows-aware entrypoint wiring for supervised sessions.
  src/coga/commands/launch.py: Refuse --idle-timeout on Windows; route to the Windows supervisor.
  src/coga/commands/megalaunch.py: Windows picker launch path and idle-timeout warning.
  src/coga/commands/ticket.py: Ticket-driven sessions use the Windows supervisor.
  src/coga/git.py: Keep Git auto-maintenance attached for Coga's Git calls on Windows.
  src/coga/launch.py: Plan Windows agent argv (full prompt or pointer) and supervise sessions natively.
  src/coga/megalaunch.py: Windows key input, resize poll and Ctrl+C handling in the picker.
  src/coga/oscompat.py: Windows process and console helpers.
  src/coga/recurring_runner.py: Windows termination through the Job Object.
  src/coga/repl_supervisor.py: Dispatch to the Windows backend; shared outcome types.
  src/coga/repl_supervisor_nt.py: New native Windows supervisor.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Owner doc; CRLF step-skill checkout still equals its owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Owner doc for the Windows launch boundary.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Owner doc; link to README native Windows notes.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Owner doc for the Windows launch contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Owner doc for Windows scheduling.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Owner doc for Windows script tickets.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md: Owner doc for Windows authoring.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md: Owner skill for the AWS Windows clean-install box.
  src/coga/usage.py: Map backslash and colon in Claude transcript dir names.
  tests/conftest.py: Windows fixture letting agent fakes reach the Windows spawn path.
  tests/test_checkouts.py: Windows launch-boundary coverage.
  tests/test_cli.py: Windows CLI coverage.
  tests/test_create.py: Platform-neutral fixtures.
  tests/test_edge_distribution.py: UTF-8 git log decode and a 120 s bound for the native installed-wheel trim.
  tests/test_git.py: Attached maintenance env tests; ignore Windows' extra index-mode probe.
  tests/test_launch.py: Windows launch, timeout and refusal coverage.
  tests/test_launch_restart.py: Windows restart coverage.
  tests/test_launch_script.py: Windows script-ticket coverage.
  tests/test_megalaunch.py: Windows picker coverage; stale skip removed.
  tests/test_packaging.py: LF carrier writes; twin checks.
  tests/test_recurring.py: Windows termination coverage.
  tests/test_repl_supervisor.py: Mark POSIX PTY mechanics POSIX-only.
  tests/test_repl_supervisor_nt.py: New Windows supervisor contract tests.
  tests/test_ticket.py: Windows ticket-session coverage.
  tests/test_trim_log.py: LF fixture writes and a 60 s native trim join.
  tests/test_usage.py: Windows transcript naming and shallow repo dirs for MAX_PATH.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: The workflow has no independent code-review step before open-pr; the owner reviews the PR. Design was evaluated by another agent, which is not code review.
checks:
  - command: uv run --extra test python -m pytest -q -p no:cacheprovider
    status: passed
    head: 8ab6297fc1e2076fc0ffeebb6ecf09e1fd7c71c7
    base: c00329d051a38dc4f320fc902d0d058703bc436a
    detail: Linux full suite, 4719 passed, 33 skipped.
  - command: uv run python -m pytest -q -p no:cacheprovider --junitxml junit.xml
    status: passed
    head: 8ab6297fc1e2076fc0ffeebb6ecf09e1fd7c71c7
    base: c00329d051a38dc4f320fc902d0d058703bc436a
    detail: Native Windows full suite on Windows Server 2025 24H2 (AWS i-05dc25bc97681ef1b, ami-0b5f645abc199e666, us-east-1a), Python 3.11.18, Git 2.56.0.windows.4; 4649 passed, 103 skipped (POSIX-only), 3 h 18 m.
  - command: attended coga launch over ssh -tt from a host PTY (see Implement phase 2 session 2)
    status: passed
    head: a469b51f7f81c52326b6a6164ba7fcffaad13fa4
    base: ee4f104b41d9ea0f9c7b7ec88d14f1257071a347
    detail: >-
      On the same box against a469b51f7 and its follow-ups 59b43c47e/9b8a27e4b: idle-timeout refusal (exit 2, no sweep), max-session 124,
      picker keys/resize/q/Esc/Ctrl+C, bump to an owner step, mark done, block, two-session chain,
      Ctrl+C passthrough, SSH hang-up without orphans, DWORD 0xC0000005/0xC000013A/7 via coga.exe and
      python -m coga.cli. Later commits changed tests and Git maintenance env only.
```
