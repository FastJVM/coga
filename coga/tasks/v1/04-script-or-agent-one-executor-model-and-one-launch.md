---
title: 'Script or agent: one executor model and one launch loop'
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
- coga/launch
- coga/script-tickets
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (evaluate-design)
agent: claude
launch_generation: pending:81eef652-6cb1-443c-88d9-021686903695
---

## Description

Follow-up to the plain-Git ticket. Make script and agent two executors of one step model, deterministic by default, and collapse launch's three step loops and mode flags into one loop with callers. Owner finds the current script/ticket model unsatisfying; this ticket redesigns it.

Depends on `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: read
its "Target model" and "Owner decisions" first. That ticket removes Git
from the kernel; this one reshapes what remains of launch. **Implement this
ticket only after v1/03 has merged**, and build on its merged code. This spec
does not repeat the deletions v1/03 owns: claims, leases, the control relay,
the checkout boundary, the chat guard, exit 75, publication and re-parking of
blocked tickets. It also takes v1/03's `run:` steps and blocked-launch rule as
given. Where v1/03's final shape differs from its spec, follow its merged code
and record the difference on the blackboard.

This ticket owns what v1/03 left to it (v1/03 "Out of scope" and its
evaluator item 5): the single step loop, the executor shape, environment
consolidation, mode flags, the done sentinel, the terminal-status probe and
`coga exit`.

### Settled (owner, 2026-11-19)

- A ticket is a script, an agent, or text. Deterministic by default: an
  agent is called only for judgment. Rationale: a script computes once; an
  LLM recomputes the whole model per token, which is waste when it sits at
  the core of routine work (crons, opening PRs).
- The documented hybrid chaining in `coga/script-tickets` stays. A failure
  is not escalated inside the ticket: it becomes another ticket.
- **Agent session end: the session ends itself, explicitly.** The
  supervisor passes the agent's PID (`COGA_AGENT_PID`). `mark`, `bump` and
  `block` only write the ticket and know nothing about sessions, because a
  `coga chat` or coordinator session changes other tickets without ending.
  When the agent has finished its step it runs `coga exit`, which SIGTERMs
  that PID (name confirmed by the owner; `suicide` rejected for a public CLI
  and because it trips model safety behavior). An agent that forgets leaves
  the session open until the human or the idle limit closes it; that costs
  time, not tokens. The supervisor only spawns, waits, then re-reads the
  ticket to decide what follows (status or step changed: chain; otherwise
  normal exit or crash), plus idle and max-session limits. A `<END>` stdout
  marker was rejected: tool output is captured by the agent CLI, rendered
  with escapes, prone to false positives, and invisible on Windows.
- **Git helpers are workflow steps.** v1/03 decision 13 settled this: a step
  may declare `run: <name>`. Here `run:` becomes one input to the script
  executor.

### Target model (this design)

1. **A step has up to two executors, always in this order: script, then
   agent.** The script executor is chosen per step: the current step's
   `run:` skill (`run.py`) when declared, else the task's sibling
   `ticket.py`, else none. It runs at most once per step per launch, as
   today. The agent executor is the step's derived agent operator. An
   owner-held step has no executor: the loop stops there ("text").
2. **One rule after every executor: re-read the ticket.**
   - Ticket gone, or status no longer `in_progress` or `blocked`: stop.
   - Step changed: start the new step, subject to the stop rules below.
     State wins over exit code. Agent CLIs report SIGTERM inconsistently,
     so an agent that bumped and was then ended by `coga exit` chains even if
     its exit code is non-zero.
   - Step unchanged: run the step's next executor. After a script, that is
     the agent, which is the documented hybrid. After the agent there is no
     next executor, so the loop stops with reason `unchanged`. That is
     exit 0 when the session ended normally (exit 0 or SIGTERM) and a crash
     (its exit code) otherwise. Megalaunch reports it as `stopped`, not
     `failed` (see Open Questions). This replaces today's split, where
     "unchanged" means "agent continues" after a script and "failure" after a
     megalaunch agent.
3. **One loop, many callers.** `launch.run_ticket(cfg, ref, options)` is the
   only step loop. The CLI, megalaunch, recurring periods, recurring
   delegation and chat call it with options; prompt-report and read-only
   dispatch never enter it.
4. **The supervisor spawns, waits and classifies, and nothing more.** It
   reports exit code, `ended` (SIGTERM, or exit 15 for the Windows wrapper)
   or `timeout` (idle or max-session limit). It knows nothing about tickets.
5. **One environment function, one script spawn, one agent spawn.**

### Acceptance criteria

Executors and environment:
- [ ] `task_env.child_env()` is the only builder of a child environment for
      a Coga-spawned script or agent. It resolves secrets and scrubs
      1Password auth through `config.build_launch_env`, then removes every
      key in a new `task_env.SESSION_ENV_KEYS`: the `TASK_ENV_KEYS`
      namespace plus `COGA_AGENT` and `COGA_AGENT_PID`. It then applies
      task metadata when a target is given, and sets `COGA_SCRIPT_TASK` for a
      stateful script. The current hand-rolled scrubs in
      `launch_script.run_script_phase`,
      `launch_script.run_bootstrap_script_help`,
      `recurring_clone.run_clone_template` and
      `authoring.invoke_ticket_authoring` call it.
      `rg -n "for key in \(\*TASK_ENV_KEYS|for key in TASK_ENV_KEYS" src`
      matches only `task_env.py`.
- [ ] `executor.run_script()` (new `src/coga/executor.py`) is the only code
      that spawns a `ticket.py` or `run:` script. The four current sites
      (`run_script_phase`'s `run_foreground_child` and `subprocess.run`
      branches, `run_bootstrap_script_help`, `recurring_clone._run_clone_script`)
      call it. It owns `128 + N` exit normalization. The clone sweep's
      timeout and output capture are parameters of it, not a second
      primitive.
- [ ] The agent executor is one function, `agent_session.run_agent_session()`
      (new `src/coga/agent_session.py`; `spawn_agent_session` and its
      command-building helpers move there from `launch.py`). The loop and
      `commands/ticket.py` authoring are its only callers.
      `repl_supervisor`, `repl_supervisor_nt` and `_nt_session_wrapper` are
      imported only by `agent_session.py` and their own tests.
      Terminal/PTY and Windows specifics stay in those modules.

One loop:
- [ ] `launch.run_ticket(cfg, ref, options) -> LoopResult` is the only step
      loop. `launch_script.run_script_chain`, `_classify_script_handoff`,
      `launch._LaunchInvocation` (with `_supervise_steps`,
      `_run_initial_script`, `_prepare_agent`), `launch._launch` and the
      `while` loop in `coga_edge/megalaunch._launch_until_stop` are gone.
- [ ] Each iteration reads the ticket once. The read after an executor is the
      next iteration's read. Each step resolves its operator exactly once into
      a `Step` record that later checks reuse. `_target_operator`,
      `_operator_display`, `_explicit_step_role` and
      `_prospective_activation_identity` are deleted or reduced to reads of
      `Step`. A test counts `resolve_operator` calls in a two-step chain
      (one per step).
- [ ] The rule in Target model §2 holds and is tested through `run_ticket`.
      If a script bumps, the next step runs. If a script leaves the step
      open, the agent runs on the same step. If an agent leaves it unchanged,
      the loop stops with `unchanged`, exit 0. If an agent bumps and exits
      non-zero, the next step still runs. If a script fails, the loop stops
      with the script's code.
- [ ] Megalaunch runs script executors. A megalaunch pick whose task has
      `ticket.py`, or whose current step declares `run:`, runs that script
      before any agent, and a deterministic bump chains without an agent.
      `tests/test_megalaunch.py` covers both.
- [ ] One `in_progress` writer. `mark.mark_in_progress` is the only code that
      sets `status: in_progress`:
      `rg -n "\"status\"\] = \"in_progress\"" src` matches only `mark.py`.
      Launch reaches it only through `launch._start()`, once per
      `run_ticket` call. `_start()` auto-activates draft or paused tickets,
      then moves `active` to `in_progress`, and leaves `blocked` alone
      (v1/03 decision 6). A test asserts one "started" log line per launch
      for both a script-first and an agent-first ticket.

Modes become callers:
- [ ] `run_ticket`'s `LoopOptions` holds caller inputs only: `agent_override`,
      `idle_timeout`, `max_session`, `max_steps`, `args` (stateless script
      operands), `conduct` (prompt conduct layer), `actor`, `agent_refusal`
      (headless recurring) and `failure_important`. The implementer may drop
      a field that turns out unused, but must not add a mode flag.
      `prompt_report`, `return_timeout`, `require_agent_target`,
      `record_launch`, `recurring_authorized`, `before_recompose`,
      `before_final_spawn` and `direct_chat` no longer exist.
- [ ] `--prompt-report` calls `launch.report_prompt(task)`, which composes
      and prints without entering the loop. `--read-only` calls
      `launch.run_read_only(task, args)`, which runs the script executor once
      for a stateless bootstrap target.
- [ ] Recurring delegation calls `run_ticket` once for its bootstrap target.
      `launch_with_before_spawn`, `_RecomposeAfterLaunchPublication` and the
      second `_launch` pass are gone. Any `launch_recurring_period` that
      survives v1/03 becomes a plain caller with no callbacks.
- [ ] The plain CLI's "period tasks need the recurring runner" refusal
      (today `recurring_authorized=False`) is a check in the CLI caller before
      `run_ticket`. The delegation path's agent-only target check (today
      `require_agent_target=True`) is a check in the delegation caller.
- [ ] `LoopResult` carries a stop reason (`done`, `handoff`, `paused`,
      `blocked`, `canceled`, `gone`, `unchanged`, `ended`, `timeout`,
      `failed`, `refused`), the exit code, a one-line detail, the last ticket
      read, and whether an agent ran. Each caller maps it: the CLI to an exit
      status, megalaunch to its summary row, recurring to period handling.

Session end:
- [ ] On POSIX the supervisor sets `COGA_AGENT_PID` in the child between
      `fork` and `exec` to `os.getpid()`, so it names the exec'd agent CLI.
      This covers both the `pty.fork` path and the non-TTY `os.fork` path in
      `repl_supervisor.run_with_done_marker` (rename it `run_supervised`).
      On Windows, `_nt_session_wrapper` sets it to its own PID before it
      starts the agent. `repl_supervisor_nt.run` terminates the job when the
      wrapper exits, so killing the wrapper ends the agent tree.
- [ ] New core command `coga exit` (`src/coga/commands/exit.py`). It reads
      `COGA_AGENT_PID`. If that PID is an ancestor of the current process
      (`oscompat.is_ancestor_process`: `/proc` on Linux, `ps -o ppid=` on
      macOS, a Toolhelp snapshot on Windows), it sends `SIGTERM` (`os.kill`;
      on Windows `TerminateProcess`) and exits 0. Otherwise it prints
      `Step finished: exit this session to continue.` and exits 0. That
      covers an unset variable, a PID that is not an ancestor (for example
      inside a PID namespace), and a refused signal. It never signals a
      process that is not an ancestor. `tests/test_exit.py` covers all four
      cases with a real ancestor child on POSIX.
- [ ] The done-signal machinery is gone: `SENTINEL_ENV`
      (`COGA_DONE_SENTINEL`), `EXPECTED_TASK_ENV`, `EXPECTED_STEP_ENV`,
      `EXPECTED_AGENT_ENV`, `COGA_SUPERVISED`, `emit_done_marker`,
      `deferred_done_marker` (and its `cli.main` wrapper), `_PENDING_INFIX` /
      `.pending-<pid>`, `_mark_completion_pending`, `completion_pending`,
      `_sentinel_signals_done`, `remove_sentinel_dir`,
      `unsignalled_advance_warning`, `launch._warn_unsignalled_advance`,
      `launch._terminal_status_probe`, `build_supervised_step_env`,
      `AgentSessionResult.done_signalled` and the `done` termination kind.
      `rg -n "SENTINEL|EXPECTED_(TASK|STEP|AGENT)|COGA_SUPERVISED|done_marker|done_signalled|terminal_status" src`
      finds nothing. `tests/test_done_marker_emission.py` is deleted.
- [ ] Inside a supervised agent session, attribution and the stale-step bump
      guard keep working. The guard is `commands/bump.py`'s check that
      refuses a bump composed for another step. Both now read the task
      metadata the session already carries: `COGA_TASK_TICKET` (path),
      `COGA_TASK_STEP` (composed step) and new `COGA_AGENT` (the spawned
      agent nickname). The presence of `COGA_AGENT_PID` is what means
      "supervised". `commands/common`'s actor derivation, `commands/bump.py`,
      `commands/owner.py` and `pr_assist.py` switch over. The existing
      attribution and stale-bump tests pass after the rename.
- [ ] `bump`, `mark`, `block`, `unblock` and `owner` print no
      "Supervised launch: …" hints and touch no session state. A stateless
      bootstrap session ends with `coga exit`. `coga mark done
      bootstrap/<name>` refuses with a message naming `coga exit` (see Open
      Questions). All packaged prompts, skills and topics that say `coga mark
      done bootstrap/<name>` say `coga exit` instead.
- [ ] `src/coga/resources/prompt-ticket.md` ("Finishing the step") and
      `prompt-megalaunch.md` say: run `coga bump` / `mark` / `block` as the
      transition, then `coga exit`. They also say an agent that forgets leaves
      the session open. The `coga/launch` topic's step-chain section states the
      §2 rule.
- [ ] Sandbox reachability is verified and recorded in `coga/sandboxes`. For
      Claude Code and Codex on Linux, with their CLI versions, record whether
      `coga exit` run through the agent's command tool ends the session or
      falls back to the message. Windows native verification follows the
      release tier in `coga-dev/testing`. The implementation PR records only
      the mocked Windows test.

Dead code and size:
- [ ] `launch._prospective_assist_ticket` and any other private function in
      `launch.py`, `launch_script.py`, `agent_session.py` and `executor.py`
      with no caller are deleted, along with re-export forwarders such as
      launch's import-only re-exports. The PR lists the deleted symbols.
      `launch_script.py` is folded into `launch.py` / `executor.py` or kept
      only if it still has a reason to exist.
- [ ] The PR description reports `wc -l` before and after for `launch.py`,
      `launch_script.py`, `repl_supervisor*.py` and `coga_edge/megalaunch.py`.

Docs and verification:
- [ ] The topics and prompts listed in Context "Docs to update" describe the
      new model. `REQUIRED_BOOTSTRAP_CONTEXT_REFS` and
      `tests/required_package_resources.txt` still match.
      `coga-dev/microkernel` "Open command placements" lists `coga exit` with
      its reason (it reads the supervisor's env contract, which must be
      co-versioned with the package).
- [ ] `python -m pytest` passes and `coga validate --json` reports no
      errors. The PR lists both commands with results.

### Proposed shape

Work in this order. Each stage keeps the suite green, so the PR reads commit
by commit.

**§1 One environment function.** In `task_env.py`, add
`SESSION_ENV_KEYS = (*TASK_ENV_KEYS, "COGA_AGENT", "COGA_AGENT_PID")` and

    def child_env(cfg, *, secrets, ref=None, ticket=None, script=False) -> dict[str, str]

It calls `build_launch_env(cfg, secrets)`, pops `SESSION_ENV_KEYS`, applies
`build_task_env(cfg, ref, ticket)` when `ref` is given, and sets
`SCRIPT_TASK_ENV` when `script` and `ref` is not a `BootstrapRef`. Callers add
their own extras afterward: the help marker, the clone scope variables, the
assist keys that survive v1/03, and `COGA_AGENT` for an agent step. Migrate
the four scrub sites named in the acceptance criteria. Authoring keeps
passing no secrets (`secrets=None`) and the parent environment as today.

**§2 One script spawn.** New `src/coga/executor.py`:

    class ScriptExit(NamedTuple): code: int; output: str | None
    def run_script(argv, *, cwd, env, timeout=None, capture=False) -> ScriptExit

Build it on `process_relay.run_foreground_child`, which already defers SIGINT
and forwards SIGTERM, so stateful scripts gain the same interrupt behavior as
stateless ones. Use the `oscompat.ProcessTree` path that
`recurring_clone._run_clone_script` uses when `timeout`/`capture` is set.
Move `_normalize_exit_code` here. Also add `script_for_step(ref, ticket) ->
Path | None`: the `run:` skill's `run.py` when the current step declares one
(v1/03's resolver), else `ticket.py`. It replaces `script_entry_point` at
every caller.

**§3 Session end.** Add `coga exit` and `oscompat.is_ancestor_process(pid)`.
In `repl_supervisor`, set `COGA_AGENT_PID` in the forked child before
`execvpe` (both fork paths). Do the same in `_nt_session_wrapper` before its
`subprocess.run`, and have `repl_supervisor_nt.run` terminate the job when the
wrapper exits. Delete the sentinel directory, polling and `.pending-`
machinery listed in the acceptance criteria. The classifier returns `exit`
(with code), `ended` (SIGTERM / `128+15`, or Windows wrapper exit 15) or
`timeout`. Switch attribution, the stale-step guard, `owner` and `pr_assist`
to `COGA_TASK_TICKET` / `COGA_TASK_STEP` / `COGA_AGENT` / `COGA_AGENT_PID`.
Delete `emit_done_marker` calls from `commands/bump.py`, `commands/mark.py`
and `commands/block.py`, the "Supervised launch" hints, and
`cli.main`'s `deferred_done_marker` wrapper. Make `mark done bootstrap/<name>`
refuse. Update `prompt-ticket.md`, `prompt-megalaunch.md` and every packaged
`mark done bootstrap/` instruction to `coga exit`. Then verify sandbox
reachability by hand and record it in `coga/sandboxes`.

**§4 Agent executor module.** Move `spawn_agent_session`,
`prepare_agent_launch`, `build_agent_command`, `_agent_command_parts`,
`_plan_windows_agent_command`, `agent_command_refusal`,
`require_representable_agent_command`, `AgentSessionResult` and their private
helpers from `launch.py` to `src/coga/agent_session.py`. Rename the entry
point to `run_agent_session`. Drop keyword parameters that no caller uses once
v1/03 and §3 have landed (expect `before_recompose`, `validate_before_spawn`,
`before_spawn`, `validate_after_spawn`, `after_spawn_release`,
`record_launch_on_spawn`, `commit_log`, `checkout_notice`, `assist_branch`
if v1/03 dropped assists). Point `commands/ticket.py` at the new module.

**§5 The loop.** In `launch.py`:

    @dataclass(frozen=True)
    class Step:            # derived once per iteration
        key: str | None    # ticket.step
        role: str | None   # effective role
        operator: Operator | None
        agent: str | None  # nickname to spawn, override rule applied
        script: Path | None

    def run_ticket(cfg, ref, options: LoopOptions) -> LoopResult:
        ticket = read_ticket(ref)
        # refusals before any write: terminal status, owner step without
        # override, missing TTY/CLI when the first executor is an agent
        started = False; scripted = set(); agent_steps = 0
        while True:
            step = _step(cfg, ref, ticket, options, previous)   # one resolve_operator
            if stop := _stop_before(step, ticket): return stop
            if not started: ticket = _start(cfg, ref, ticket, options.actor); started = True
            if step.script and ticket.status != "blocked" and step.key not in scripted:
                scripted.add(step.key)
                code = run_script(...).code
                after = _reread(ref)
                if code: return failed(code)
                if _changed(ticket, after): ticket = after; continue
                ticket = after                      # unchanged -> agent, same step
            if options.agent_refusal: return refused
            agent_steps += 1
            if options.max_steps and agent_steps > options.max_steps: return failed(...)
            session = run_agent_session(...)
            after = _reread(ref)
            if ref is stateless: return ended/exit/timeout from session
            if session.timeout: return timeout
            if not _changed(ticket, after): return unchanged(session)
            ticket = after

Keep today's `--agent` continuation rule: the override follows directly
consecutive steps that explicitly declare `agent`. Compute it inside
`_step()`. Keep the stop rules from `_harness_stop_reason`: owner handoff,
terminal/paused/blocked status, no workflow, unroutable operator, missing CLI
and a deleted task directory. Express them as `_stop_before()` /
`_changed()`. `_start()` wraps `_auto_activate` plus `mark_in_progress`, and
it is the only caller of `mark_in_progress` in launch code.
`launch.launch()` (CLI) resolves the target, applies the CLI-only refusals,
calls `run_ticket` and maps `LoopResult` to an exit code. Use 0 for `done`,
`handoff`, `paused`, `blocked`, `canceled`, `gone`, `ended` and a clean
`unchanged`. Use the child's code for a failed script or crashed agent, 124
for a timeout and 2 for a refusal.

**§6 Callers.**
- `commands/launch.py`: `--prompt-report` calls `report_prompt`,
  `--read-only` calls `run_read_only`, and everything else calls `launch()`.
- `coga_edge/megalaunch._launch_until_stop`: keep the exact re-read and the
  sweep gates (owner filter, status, candidate check), then make one
  `run_ticket` call with `max_steps=max_steps_per_task`,
  `conduct="megalaunch"` and an actor of `megalaunch`. Map `LoopResult` to
  `MegalaunchResult`, with `unchanged` → `stopped`. Delete the megalaunch-side
  `resolve_operator` routing, its own `in_progress`/activation write and its
  call to `unsignalled_advance_warning`.
- `recurring_runner`: delegation makes one `run_ticket` call on the bootstrap
  target after marking the period `in_progress` (through `mark_in_progress`).
  The period's completion follows the Open Questions answer. Period launches
  call `run_ticket` with `agent_refusal` for headless sweeps.
- `commands/recurring.py list` and the `retire` bootstrap `ticket.py` use
  `run_read_only` / `launch()` as appropriate.
- `coga chat` stays the alias `launch bootstrap/orient`, with no chat code in
  launch.

**§7 Delete** `_LaunchInvocation`, `_launch`, `run_script_chain`,
`_classify_script_handoff`, `_routing_identity` (its moving-sync reason left
with v1/03), `_require_agent_after_script`, `_prospective_assist_ticket` and
every helper left without a caller. Fold what remains of `launch_script.py`
(`_echo_script_iteration`, help dispatch) into `launch.py` or `executor.py`.

**§8 Docs** (see Context) **and §9 tests.** Rewrite
`tests/test_launch_script.py` and the chain parts of `tests/test_launch.py`
against `run_ticket`. Rewrite `tests/test_repl_supervisor.py` and
`tests/test_repl_supervisor_nt.py` around spawn, wait, classification and
`COGA_AGENT_PID`. Delete `tests/test_done_marker_emission.py`. Adapt
`tests/test_env_isolation.py` to `child_env`, and update `conftest.py`
fixtures that set the old env names. Add `tests/test_exit.py`, the
megalaunch script cases and the one-started-line test. Update the seeded
fixture only if its `deterministic/check.md` path changes behavior.

### Out of scope

- Anything v1/03 owns: Git, checkouts, publication, claims, leases, `run:`
  parsing and validation, the blocked-launch rule, `git/*` workflow steps.
- Changing what a script may do (the `coga/script-tickets` contract, exit
  semantics, `COGA_TASK_*` meanings) beyond the env-name swap in §3.
- Prompt composition (`compose.py`) beyond removing parameters that only fed
  deleted callbacks.
- Human-assist semantics. Whatever v1/03 keeps passes through `child_env`
  extras unchanged.
- New recurring behavior: scheduling, autofix and clone sweeps keep their
  logic and only switch to `child_env` / `run_script`.
- Windows native verification (release tier).
- Splitting `recurring_runner.py` beyond its calls into launch.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

### Codebase facts (design survey, 2026-11-20, branch at c18dbdd0d, before v1/03)

Symbols first. Module sizes are navigational and will drift once v1/03
lands. Today: `launch.py` 4,631 lines, `launch_script.py` 702,
`repl_supervisor.py` 1,055, `repl_supervisor_nt.py` 675,
`coga_edge/megalaunch.py` 2,533.

- **Three loops.** `launch._LaunchInvocation._supervise_steps` re-reads the
  ticket and calls `launch_script.run_script_chain` for each new step, then
  spawns through `spawn_agent_session` and decides chaining with
  `_harness_stop_reason`. `run_script_chain` loops scripts on its own and
  returns `needs_agent` when the step is unchanged.
  `coga_edge/megalaunch._launch_until_stop` has a third `while` loop that
  calls `claimed_session.run_claimed_agent_session` directly and never runs
  `ticket.py`. It returns `failed` with "agent exited without changing task
  state" when `(step, status)` is unchanged.
- **`_launch` phases.** `launch._launch` builds a `_LaunchInvocation` from 16
  keyword inputs and runs `_prepare_target`, `_align_and_classify`,
  `_run_initial_script` and `_prepare_agent`, then `_supervise_steps`. Its
  callers are `launch.launch` (CLI: `direct_chat` for `bootstrap/orient`,
  plus a separate `read_only` branch that calls
  `launch_script.run_script_phase`), `launch.launch_recurring_period`
  (passes `before_final_spawn=capture_launched_period_lease`,
  `recurring_authorized=True`) and `launch.launch_with_before_spawn`. The last
  one is called by `recurring_runner` delegation. It runs `_launch` once with
  `before_recompose`, catches `_RecomposeAfterLaunchPublication`, then runs
  `_launch` again with `record_launch=False`.
- **Four script spawns.** `run_script_phase` uses
  `process_relay.run_foreground_child` for stateless targets and
  `subprocess.run` otherwise. `run_bootstrap_script_help` uses
  `run_foreground_child`. `recurring_clone.run_clone_template` uses
  `_run_clone_script` (a `ProcessTree` with timeout and captured output).
- **Env scrubs.** `config.build_launch_env` is the shared base (secrets plus
  `scrub_op_auth_env`). Four callers then hand-pop `TASK_ENV_KEYS` plus the
  session keys: `run_script_phase`, `run_bootstrap_script_help`,
  `recurring_clone.run_clone_template` and
  `authoring.invoke_ticket_authoring`. `repl_supervisor.build_supervised_step_env`
  adds `COGA_SUPERVISED` and `COGA_EXPECTED_*` on the agent side.
- **`in_progress` writes.** `launch._start_session` and
  `launch_script.run_script_phase` call `mark.mark_in_progress`.
  `claimed_session` (megalaunch) calls it too and also sets the field
  directly while preparing a claim. `launch._prepare_agent` sets
  `frontmatter["status"] = "in_progress"` on a prospective copy.
- **Done signal.** `commands/bump.py`, `commands/mark.py` and
  `commands/block.py` call `repl_supervisor.emit_done_marker(session_id=slug)`.
  `cli.main` wraps every command in `deferred_done_marker()`, which writes a
  `.pending-<pid>` marker. `run_with_done_marker` polls the
  `COGA_DONE_SENTINEL` file (`_sentinel_signals_done`) and the
  `terminal_status` callback, which is `launch._terminal_status_probe`.
  `repl_supervisor_nt.run` mirrors it with `completion_pending` /
  `remove_sentinel_dir`.
- **`EXPECTED_*` consumers beyond the sentinel:** `commands/common` actor
  derivation credits `agent:<COGA_EXPECTED_AGENT>` when `COGA_SUPERVISED` and
  `COGA_EXPECTED_TASK` match the target. The stale-step guard in
  `commands/bump.py` refuses a bump when `COGA_EXPECTED_STEP` differs.
  `commands/owner.py` refuses reassignment from the ticket's own supervised
  session. `pr_assist.py` reads `COGA_EXPECTED_TASK`.
  `_human_completes_active_owner_step` and the rewind refusal in `bump.py`
  read `COGA_SUPERVISED`. Every one of these must move to the new names, not
  be dropped.
- **Spawn points for `COGA_AGENT_PID`.** `repl_supervisor.run_with_done_marker`
  uses `pty.fork()` then `os.execvpe` for a TTY and `os.fork()` then
  `os.execvpe` otherwise, so the child can set its own PID before exec. On
  Windows, `oscompat.ProcessTree(interactive=True)` runs
  `_nt_session_wrapper.py`, which joins the Job and then spawns the agent.
  `_TTY_SANITIZE` already resets the terminal after a kill.
- **Megalaunch conduct.** `compose.LaunchContext` is
  `Literal["attended", "megalaunch", "recurring"]`. It selects
  `prompt-attended.md`, `prompt-megalaunch.md` or `prompt-queue.md`.
- **Dead code.** `launch._prospective_assist_ticket` has no references.
- **Stateless completion.** `coga mark done bootstrap/<name>` is the
  documented end of an agent-backed bootstrap session (`coga/cli` "Stateless
  command completion"). Recurring delegation finalizes the period only when
  the launch kind is `done`, which comes from that signal.

### Docs to update

User topics (package copies under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/`):
- `launch` (step chain, options and exits, the §2 rule)
- `script-tickets` (Chaining, Completion attribution, `COGA_TASK_*` contract
  with `COGA_AGENT` / `COGA_AGENT_PID`)
- `cli` (replace "Stateless command completion" with `coga exit`; add the
  command)
- `megalaunch` (script phase, `stopped`)
- `recurring/delegation` and `recurring/scheduling/inactivity`
- `lifecycle` (no session side effects)
- `sandboxes` (signal reachability findings)
- `edge-code` and `notifications/producers` (done-marker mentions)

Prompts and packaged tickets: `prompt-ticket.md`, `prompt-megalaunch.md`,
`prompt-queue.md`, and the `bootstrap/slack`, `bootstrap/address-pr-comments`
and `bootstrap/resolve-conflicts` tickets.

Coga-dev: `coga-dev/internals/agent-spawn` (rewrite around executor/loop),
`coga-dev/internals/compose`, `coga-dev/codebase` (source map: `executor.py`,
`agent_session.py`), `coga-dev/codebase/gotchas`, and `coga-dev/microkernel`
("the ticket.py script phase" and the `coga exit` placement). Before editing,
re-run `rg -l "mark done bootstrap|done sentinel|COGA_SUPERVISED|COGA_EXPECTED"`
over `src/coga/resources docs/contexts`, because v1/03 rewrites some of these
files.

<!-- coga:blackboard -->

## Open Questions

Design step, 2026-11-20. Recommendations first; the owner decides in review-design.

1. **Delegated recurring period completion without a done signal.** Today
   `recurring_runner` finalizes a delegated period only on launch kind `done`
   (from `coga mark done bootstrap/<name>`). With `coga exit` the supervisor
   cannot tell "agent finished" from "human closed it". Recommend: mark the
   period done when the delegate session ended without a timeout and with
   exit 0 or SIGTERM (`ended`), and leave it `in_progress` on a crash or
   timeout as today. Alternative: export the period slug to the delegate so
   it runs `coga mark done <period>` itself before `coga exit`.
2. **`coga mark done bootstrap/<name>`.** Under "mark only writes the ticket"
   it has nothing to write. Recommend refusing it with a pointer to `coga
   exit` (the spec assumes this). Alternative: keep it as an audit-only line
   that does not end anything.
3. **Megalaunch `unchanged` = `stopped`, not `failed`.** With an explicit
   `coga exit`, an agent or human ending a session without a bump is an
   ordinary stop. Confirm. This changes megalaunch's summary counts. Check
   whether dependency retry keys on `failed` before implementing.
4. **`coga exit` in core.** It reads the supervisor's `COGA_AGENT_PID`
   contract, which must be co-versioned with the package, so the spec puts it
   in `src/coga/commands/` and lists it under microkernel "Open command
   placements". Confirm.
5. **`COGA_SUPERVISED` → presence of `COGA_AGENT_PID`, and `COGA_EXPECTED_*`
   → `COGA_TASK_TICKET` / `COGA_TASK_STEP` / new `COGA_AGENT`.** Coga skills
   or adopting repos that read the old names break. The packaged
   `script-tickets` and `lifecycle` topics document them. Accept the rename
   with no compatibility alias? Recommend yes (pre-1.0).

## Design notes

- Spec written against the pre-v1/03 tree (branch at c18dbdd0d). Implement
  only after v1/03 merges; its review-design is still open. Evaluator items 2
  and 4 there (legacy `implement` fallback, `run:` dispatch in megalaunch and
  delegation) overlap §5/§6 here. If v1/03 resolves `run:` dispatch through
  the old loops, this ticket moves it into `run_ticket`.
- Considered and rejected: signalling the supervisor (`COGA_SUPERVISOR_PID`)
  instead of the agent, because the owner chose the agent PID. Also rejected:
  setting `COGA_AGENT_PID` from the parent after spawn, because the child env
  is fixed at exec. The fork-child-sets-own-PID approach needs no new
  primitive.
- Ancestor check in `coga exit`: a Linux command sandbox with its own PID
  namespace (for example bubblewrap) would otherwise make `os.kill` hit an
  unrelated in-namespace PID. Refusing non-ancestors makes the sandbox case
  fall back to the message.
