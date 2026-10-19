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
      and the ticket advanced exactly one step. Separate runs show the same
      for `coga mark done` and `coga block`. After each run, the Job's active
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
      - A Python caller that passes `idle_timeout` (megalaunch, recurring)
        gets one `[coga watcher]` warning that idle-timeout is unavailable
        on Windows, and the session runs with `max_session` only.
- [ ] **Interrupts.** While a Windows session runs, Ctrl+C reaches the
      agent as input (Claude Code shows its own "press again to exit"), and
      the `coga` parent does not raise `KeyboardInterrupt`. Closing the SSH
      connection mid-session leaves no orphaned agent processes, because
      the Job is kill-on-close.
- [ ] **Megalaunch picker** works over `ssh -tt`: ↑/↓/j/k move, Space
      toggles, `a`/`n` select all/none, Enter confirms, and `q`/Esc/Ctrl+C
      quits. A terminal resize redraws within about 0.2 s.
- [ ] **Large prompts.** A composed prompt larger than the Windows
      command-line budget reaches the agent through the existing
      prompt-file pointer, not a `CreateProcess` failure. An agent CLI that
      resolves to a `.cmd`/`.bat` shim (npm-installed Codex) always gets
      the pointer.
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
      POSIX supervisor path is byte-for-byte behavior-unchanged.
- [ ] **Docs** (canonical and packaged twins in sync, `tests/test_packaging.py`
      green):
      - `coga/install` lists native Windows as supported and adds a
        Windows baseline (see *Proposed shape* §7).
      - `coga/internals/agent-spawn` describes the Windows supervisor.
      - `coga/launch` notes the Windows idle-timeout refusal under
        *Options and exits*.
      - `coga/codebase` lists the new module.
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
      fixed before merge.

### Proposed shape

1. **The platform split stays behind `run_with_done_marker`.** Its
   signature, `ReplOutcome`, `emit_done_marker`, `_sentinel_signals_done`,
   and the sentinel protocol stay unchanged. At the top of
   `src/coga/repl_supervisor.py` `run_with_done_marker()`, branch with
   `if os.name == "nt": return repl_supervisor_nt.run(...)`, passing every
   argument through. Do it after the existing argument validation. The
   POSIX body below is untouched. Callers (`launch.spawn_agent_session`)
   do not change.
2. **New module `src/coga/repl_supervisor_nt.py`.** It is the Windows
   backend and is imported lazily, so POSIX never loads it. It is
   core infra by the microkernel rule, because it is half of the shared
   supervisor that every agent-spawn caller goes through. Its flow:
   - **Spawn.** The child inherits stdin/stdout/stderr (no PTY, no proxy)
     and the complete `env` plus `SENTINEL_ENV`, the same as POSIX. Start
     it through `oscompat.ProcessTree` (the Job Object with
     `KILL_ON_JOB_CLOSE` and the join-the-job wrapper from the core
     ticket) with `CREATE_NEW_PROCESS_GROUP`. Resolve `cmd[0]` with
     `shutil.which`, so `.exe`/`.cmd` resolve the way the POSIX path's
     `execvpe` does. A missing binary raises `AgentCliNotFound(cmd[0])`,
     matching the non-TTY branch.
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
     box.
   - **Wrapper.** The wrapper sets `SIGINT` and `SIGBREAK` to `SIG_IGN`
     before it waits, so a CTRL_BREAK stops the agent while the wrapper
     survives to propagate the agent's real exit code. Without this,
     Python's default CTRL_BREAK handling kills the wrapper first.
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
3. **`oscompat.ProcessTree` (core ticket) grows only what the supervisor
   needs**: an optional held-start gate, an optional new process group,
   and a graceful `interrupt()` (CTRL_BREAK on Windows) separate from
   `kill()`. Existing consumers (`recurring_clone`, `recurring_runner`)
   keep their current calls and behavior. Keep the wrapper short. It
   counts against the Windows command-line budget in §5, so if it is a
   `-c` string, keep it to a few hundred characters, or move it to a
   tiny importable module run as `python -m`.
4. **`coga launch --idle-timeout` refusal.** In
   `src/coga/commands/launch.py`, when `os.name == "nt"` and
   `idle_timeout is not None`, exit 2 before calling `_launch`, so no
   state changes. The message names the limitation and suggests
   `--max-session`. Python callers are not refused (§2 warns instead).
5. **Prompt delivery on Windows.** In `src/coga/launch.py`,
   `_argv_prompt()` currently compares UTF-8 bytes with
   `_MAX_PROMPT_ARG_BYTES` (the Linux `MAX_ARG_STRLEN` bound).
   `CreateProcess` instead caps the *whole* command line at 32,767 UTF-16
   units, after `subprocess.list2cmdline` quoting and including the
   wrapper. On Windows, use a separate budget of about 24,000 UTF-16
   units for the prompt, chosen to leave headroom for the wrapper, the
   discussion template and flags. Name it beside the existing constant,
   and verify the headroom on the box. When `build_agent_command`'s
   resolved CLI ends in `.cmd`/`.bat`, always use the pointer: `cmd.exe`
   caps lines at 8,191 characters and expands `%`/`^`/`&`. Check that the
   pointer text (a prompt-file path plus fixed prose) contains no cmd
   metacharacters; the temp path can contain spaces, which quoting
   handles. POSIX keeps today's rule.
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
     - natural exit passes the code through;
     - an NTSTATUS crash gives `crash`;
     - the gate holds the child until release, and admission failure
       kills it with the rollback called;
     - console modes are restored;
     - `done_signalled` is latched after exit;
     - an idle-timeout warning is emitted.
   - Add Windows cases for the picker's key mapping and resize poll in
     `tests/test_megalaunch.py` (monkeypatch `msvcrt`), plus the
     `--idle-timeout` refusal and the `.cmd` prompt-pointer rule.
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
   - PowerShell or Windows Terminal as the shell (Coga needs no bash);
   - agent CLIs: Claude Code's native installer is the tested agent;
     Codex is untested on native Windows;
   - the `--idle-timeout` limitation.
   Also update `coga/internals/agent-spawn` (*The supervisor* section),
   `coga/launch` (*Options and exits*: the Windows idle-timeout refusal),
   and `coga/codebase` (the new module). Check each one's packaged twin.

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
  chain*, *Options and exits*) and `coga/internals/agent-spawn` (*The
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
  `coga/internals/launch-claims` ("Held child and admission", currently
  pipe-specific) and `coga/testing/clean-install/windows-aws` ("RDP",
  currently directing attended launch there), with packaged twins.
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
