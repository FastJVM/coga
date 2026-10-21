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
step: 3 (review-design)
agent: claude
---

## Description

Make interactive agent sessions work on native Windows, then declare Windows
supported. That covers `coga launch` of an agent step, `coga chat`,
`coga build`, `coga ticket`'s authoring session, and `coga megalaunch`
with its picker. This is the last of the three port tickets. It
builds on `windows-native/core-port-cli-and-test-suite-pass-on-native-window`,
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
      `marketing/fix-installer/test-and-fix-install-on-macos-and-windows`'s
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
- WSL, macOS changes, and CI (`windows-native/pr-ci-with-linux-and-windows-test-jobs`).
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

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


Final checks: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.cli validate --task windows-native/interactive-coga-launch-on-native-windows --json` exited 0 (one task, no issues); `git diff --check` passed. The final `git fetch origin main` introduced no further changes.

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
windows-native/interactive-coga-launch-on-native-windows --json` exited 0
(one task, no issues); `git diff --check` passed. Local assertions confirmed
unchanged frontmatter, one blackboard fence, the required composable
Description subsections, and positive/negative exact-marker matching for
the U+2028 batch pointer.
