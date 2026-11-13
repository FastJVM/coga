---
title: Decompose launch into substrate plus ticket orchestration
status: active
owner: nicktoper
agent: codex
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga-dev/codebase/gotchas
- coga-dev/testing
- coga-dev/microkernel
- coga-dev/project-stage
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 2 (review-design)
---

## Description

Finish separating the generic ticket executor from the procedures that use
it. The CLI/service split already shipped; the remaining work is in
`src/coga/launch.py`, its consumers, and the boundary between stateless command
tickets and stateful workflow execution. Prompt-form experiments and their
production assembly migration now have their own numbered group at
`v1/microkernel/03-prompt-assembly/`; this ticket retains the distinct shared
execution and stateless invocation contracts. This is a scope proposal for
owner review, not approval to resume the paused implementation.

### Objectives advanced

Ticket ownership: callers should own their procedure and defaults. Hackability:
a customized ticket must use the same executor without adding a core case.
Simplification: remove duplicated preparation and command-specific branches;
a module split alone does not complete this ticket.

### Boundary with prompt assembly

The numbered `03-prompt-assembly/README.md` group owns candidate prompts,
the comparison protocol, bounded trials and any production assembly migration.
Its first result may be that no replacement is justified. This ticket owns
stateless invocation/configuration/publication, session/admission seams and
removal of duplicated execution setup. Consume the selected shared assembler
without designing a second applicability mechanism here.

Prompt experiments use the current executor and do not wait for this refactor.
Design the stateless contract independently with read/report, customization,
lifecycle and orchestration consumers. A runtime change here that depends on
a new prompt contract waits for the group's positive experimental decision
and coordinates its interface with the assembly implementation ticket.

### Premise check against main

Snapshot: `49b34b229` (2026-11-12); physical line counts include blanks and
comments, exclude tests/docs, and describe inventory rather than promised savings.

1. The subject exists: the large shared runtime remains.
2. The old path and API inventory drifted. `commands/launch.py` is now a
   100-line adapter; `launch.py` is the 4,577-line service. `launch_script.py`
   is 620 lines. `agent_session.py` and `script_session.py` do not exist.
3. The prior plan is retained under Superseded designs. Its substance is
   restated here; retired tickets and archived audit pages are not dependencies.
4. Part shipped in `b3007ef2e`: the plain Python launch API, result/error
   boundary and thin Typer adapter. Drop that extraction from remaining work.
   Production callers now import `coga.launch`, not `commands.launch`.

### Current responsibility inventory

| Surface | Current responsibility | Proposed boundary |
| --- | --- | --- |
| `launch.launch`, `_LaunchInvocation`, `LaunchResult`, `LaunchBail` | Target admission, preparation, workflow chaining, refresh and outcomes | Generic supervisor; preserve the public seam rather than creating a second launch service |
| `spawn_agent_session`, `AgentSessionResult`, `build_agent_command`, command representability and usage helpers | One composed agent process; shared with authoring and megalaunch | Proposed session-module boundary, subject to prompt-comparison findings; migrate real callers together if extracted |
| `launch_script.script_entry_point`, `run_script_phase`, `run_script_chain` | Exact `ticket.py` classifier, execution, refresh and handoff | Keep the existing classifier; split raw execution only if it removes duplication or lifecycle coupling |
| Shared composition consumed by launch and authoring | Prompt construction and applicability | Owned by the numbered prompt-assembly group; consume its selected seam without duplicating it |
| `checkout_policy.select_checkout_policy` (145 lines), `checkouts.py` (1,159 lines) | Select policy from shipped names/instruction equality; perform shared Git mechanics | The dedicated checkout-policy ticket owns declaration and compatibility; this ticket consumes its result |
| `DISCUSSION_BOOTSTRAP_TICKETS`, `_bootstrap_kickoff`, direct-chat and onboarding cases | Named procedure defaults and special behavior | Move defaults to their owning ticket/caller where possible; retain the actual chat lock/receipt and admission guarantees in shared machinery |
| `launch_recurring_period`, `launch_with_before_spawn`, `settle_delegated_period` | Recurring leases, publication and held-child admission | Keep explicit typed contracts; queue selection and scheduling remain caller policy |
| `_format_prompt_report`, push-auth preflight, agent skill-view refresh | Diagnostics and execution readiness | Reports belong to the read/report sibling; support classification belongs to the support sibling; required point-of-use checks remain enforced |

Callers to migrate together with any session extraction: `commands/ticket.py`,
both megalaunch modules, `recurring_runner.py`, and the packaged
`bootstrap/retire/ticket.py`. `cli.py` also consumes `checkout_guard_scope`.
Several callers still use private service helpers; eliminate those dependencies
through the existing shared operations, not forwarding imports in command files.

### Proposed changes and contracts

1. Retain one generic supervisor and expose the one-session executor already
   shared by real callers. Reduce its caller-specific setup only where the
   callers can converge without losing their admission/publication semantics.
   A session extraction is a proposed means, not a prerequisite for prompt
   experiments or an end in itself. Coordinate boundaries with the assembly
   ticket once its contract has experimental support.
   No plugin host, phase registry, or new callback framework.
2. Establish the minimal stateless command-ticket execution contract needed
   by the read/report and customization tickets. Today `launch` loads a user
   config and its CLI exit normally sweeps state; a read command currently
   needs neither publication nor a configured user. A blind alias therefore
   changes behavior. Design explicit generic invocation policy for this
   distinction, with no command-name allowlist, before migrating those heads.
   Source inspection/help must remain usable with dirty state, no agent/TTY,
   and no Git writes. A write command retains its publication boundary.
3. Coordinate the narrow completion seam with lifecycle and orchestration.
   Script launch clears the outer supervisor/expected-task environment. A
   nested command ticket cannot silently become `block`, `bump`, or a
   bootstrap-completing `slack` call. Preserve the existing completion
   primitives until a reviewed equivalent proves identity and termination.
4. Keep stateful script behavior intact: a script completes its own step
   through the lifecycle CLI; exit zero alone never advances or finishes it.
   An unchanged open step falls through to the agent. Skills never supply
   executable launch plugins, inline scripts, or a static script/agent flag.
5. Consume shared composition through the prompt-assembly group's selected
   seam when moving session callers. This ticket does not select a prompt
   form or migrate noninteractive autofix assembly; those belong to that
   group's actual implementation ticket. Keep this change's admission,
   publication and completion responsibilities explicit.
6. Preserve native Windows console/Job Object behavior, POSIX supervision,
   environment isolation, secret injection/redaction, startup publication,
   assist receipts, recurring leases and released launch claims. The old
   "no locks exist" inventory is obsolete: direct chat has a checkout guard.

### Acceptance and reduction evidence

- [ ] Session changes consume the approved shared composition seam without
      adding a competing prompt assembler or moving the experimental gate
      into hidden kernel rules. Any required interface is agreed with the
      assembly ticket before dependent implementation.
- [ ] Thin command adapter remains thin; no duplicate public launch API or
      compatibility re-export is added.
- [ ] Caller policy is editable beside its ticket where selected by design;
      each retained named special case has its concrete invariant recorded.
- [ ] Read-only stateless dispatch and write dispatch have explicit, tested
      config, stream, exit, publication and checkout behavior.
- [ ] At least one real dependency/duplicate path is removed; report the
      whole-system evidence required by `coga-dev/microkernel/objectives`.
- [ ] Existing launch, restart, script, authoring, megalaunch, recurring,
      environment and supervisor tests exercise the moved boundaries. Use the
      full-suite and native Windows receipts required by `coga-dev/testing`.
- [ ] Update `coga/launch`, `coga/script-tickets`, the checkouts/publication
      owners and local source map where their execution contracts actually
      change; prompt/instruction owner changes belong to the assembly ticket.

## Context

The owning scope is this ticket; workflow checkout declaration belongs solely
to `declare-each-workflow-step-s-checkout-policy-in-th`. Its implementation can
precede the session extraction. Read/report and customization depend only on
the stateless contract they need; recipe job moves need no new session API.

Keep the existing paused status, owner `review-design` step and frozen
workflow. The owner reviews this narrowed execution scope separately; neither
authoring the new drafts nor completing their experiment approves this ticket's
runtime implementation. This remains a real execution deliverable, not an
umbrella ticket for the new directory.

The following editing targets are cited rather than attached; read their
named sections before designing changes and update their owners in the same
implementation PR:

- `coga/launch`,
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md`:
  "Phases and routing", "Agent preflight order", "The step chain", and
  "Options and exits". Agent readiness checks must still precede startup
  writes; a stateless target never acquires workflow chaining.
- `coga/script-tickets`,
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md`:
  "One deterministic phase", "Chaining", and "COGA_TASK_* contract".
  `launch_script.run_script_phase` precedes agent preparation, exit zero does
  not advance a stateful step, and script children must not inherit authority
  to terminate an outer supervised session.
- `coga-dev/internals/agent-spawn`,
  `docs/contexts/coga-dev/internals/agent-spawn/SKILL.md`: "Launch API and
  phases", "Order inside one call", "Per-caller parameters", "Large prompts",
  and "The supervisor". `spawn_agent_session` owns one session; its callers
  have distinct admission and publication contracts. Preserve command-line
  representability checks before effects and the supervisor's completion
  channel when moving composition or session code.
- `coga-dev/codebase`, `docs/contexts/coga-dev/codebase/SKILL.md`: "Source map"
  and "Contribution rules". Migrate real callers with a shared extraction;
  update the source map instead of leaving a second API in a command module.
- `coga/checkouts`,
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md`:
  "Start, work, end" and "Which checkout you invoke Coga from". Shared
  checkout mechanics and truthful runtime notices remain required; the
  checkout-policy sibling owns replacement of the hidden policy table.
- `coga/state-publication`,
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`:
  "When Coga publishes", "Control versus feature checkouts", and "Prepared
  ticket transactions". Preserve write transactions and held knowledge while
  making read-only stateless dispatch free of publication effects.

For publication implementation, cite rather than attach
`coga-dev/internals/state-publication` at
`docs/contexts/coga-dev/internals/state-publication/SKILL.md`: read
"Invariants", "The end-of-command sweep", and "Guided-authoring
finalization", plus "Ordinary managed startup" in its `publish/SKILL.md`
leaf. `cli._should_sweep_coga_state` currently selects sweeping command heads;
moving a read command under launch must not silently enable that sweep.
`authoring.finalize_authored` validates changed tickets and publishes their
required knowledge together; a refusal withholds the general sweep.
`launch._LaunchInvocation._publish_startup` groups ordinary managed startup before checkout
entry. Use the linked user `state-publication/launch-boundaries/SKILL.md`
classification and the implementation `log-writers/SKILL.md` inventory when
changing any caller's publication order.

Drop the already-shipped Typer/service split, removed `project` caller,
skill-backed script resolution, automatic script completion, duplicate live
definitions and archive-audit editing from this implementation scope. Defer
cosmetic file splits and broad renames that advance none of the objectives.

<!-- coga:blackboard -->

## Verification — 2026-11-12 authoring session

Full Linux suite receipt: base commit `9ab4cfa420d1ee4914fa539b14dcb8a06ec5e8a3`, with ticket/index-only working-tree edits (not a clean-commit receipt); Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12.
Command: `TERM=dumb PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest --basetemp=/home/n/Code/coga-pytest-prompt-group-20261112-0250`.
Result: **4853 passed, 33 skipped, 0 failed**, 761.20 seconds. Full output: `/tmp/coga-prompt-group-pytest-20261112-0250.log`.
Python 3.11 was not used. This authoring session changes only tickets and indexes, with no platform-sensitive runtime implementation or native Windows claim.

Four scoped validations pass. The repo-wide read-only validation reports 87 valid tasks, no errors, and 18 warnings; the three new drafts have only the expected unfrozen-workflow warning. Discovery finds exactly three grouped tickets and no group-root task; README links and `git diff --check` pass. These checks cover ticket organization, not experimental superiority of a prompt candidate.

The earlier suite on base `4c691e8bcaaddbb1d75d38fa7dbd6a8dd62ccd22` with ticket-only edits passed 4853 tests, skipped 33, and failed none in 929.22 seconds on the same platform/interpreter. Output: `/tmp/coga-launch-authoring-pytest-20261112-0206.log`. Receipts remain tied to their actual bases; later state-only reconciliation is not another suite receipt.

## Scope handoff — 2026-11-12

The owner accepted inclusion of noninteractive autofix, a paired trial protocol,
and explicit invocation facts, then asked for numbered experimental tickets.
The prompt work now lives in the plain `03-prompt-assembly/` directory; this
ticket retains stateless invocation/publication and execution decomposition.
Its paused lifecycle and frozen workflow position are unchanged. No runtime
implementation or prompt trial has run in this authoring session.

The owner confirmed the numbered group. Its cold review found no blocking
issue; the autofix contract citation and durable-decision handoff are now in
the new ticket bodies. The comparison protocol also names observable behavior,
source-identification tasks, payload and implementation-simplicity measures;
fixed repetitions and a minimum useful effect remain for its owner review.
All three new tickets remain drafts. Candidate trials have not run.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

`src/coga/commands/launch.py` is currently both the `coga launch` Typer command
and the shared runtime used by task launches, `coga ticket`, and `coga
megalaunch`. Its 3,782 lines (1,179 when this was designed) combine target/status policy, workflow
supervision, prompt/agent process execution, usage capture, git readiness and
refresh behavior, and lifecycle writes. Script execution adds another 600
lines in `src/coga/launch_script.py`, including both subprocess mechanics and
step/status transitions. The resulting command module is a dependency of other
commands and makes every launch-adjacent behavior look irreducibly core.

Decompose that implementation around the actual bootstrap boundary. A ticket
cannot execute the ticket that implements ticket execution, so Coga still
needs a small Python executor and a thin addressable `coga launch <target>`
head. That is the specific exception proved by this ticket; it does not make
activation policy, blocked-task handling, git preflights, diagnostics, or
batch liveness defaults part of the executor substrate. Workflow order,
assignees, skills, and script declarations remain durable file-backed policy
interpreted by the executor rather than hard-coded command cases.

The first implementation should be a behavior-preserving module split that
makes those boundaries enforceable. Lifecycle command migration and the
removal of launch-adjacent compatibility policy then proceed through the
existing sibling tickets instead of being folded into a new all-purpose
executor API.

#### Context

Directory index: `microkernel/README`.

`coga project` was removed outright (`remove-coga-build-and-project`); this
design must not preserve a seam for it, and every `project` mention below is
void.

Owner direction from the parent: keep `launch` and the things it truly depends
on, but challenge every other part of launch-shaped behavior. This ticket should
make the line concrete enough that other migration tickets do not accidentally
rebuild a large command surface around launch.

Design first. Inventory `src/coga/commands/launch.py` and adjacent modules.
Classify each responsibility as:

- executor substrate that must stay in Python;
- launch policy that can move to bootstrap ticket/workflow/skill text;
- lifecycle transition that belongs with the lifecycle migration ticket;
- compatibility sugar that can become an alias or a small wrapper.

Out of scope: moving `create`, moving `skill *`, or implementing lifecycle
verb migration unless it is required to prove the launch split.

##### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      re-inventory the current launch modules and callers, then identify
      duplicated session setup/supervision and obsolete wrappers that this
      split can remove. Report the kernel and total production-code delta
      separately. Keep the first split behavior-preserving; a size-neutral
      extraction must show a dependency reduction and name the follow-up
      responsible for each deferred simplification.

- [ ] `src/coga/commands/launch.py` is a thin Typer adapter: parse CLI values,
      resolve/report user-facing errors, invoke prompt-report or the launch
      service, and format the terminal outcome. Other modules no longer import
      private helpers from a command module.
- [ ] A command-agnostic agent-session module owns exactly one composed agent
      process: prompt materialization and oversized-argv indirection, agent argv
      construction, PTY/done-sentinel supervision, timeout outcome, usage
      capture/redaction, launch-log writes, and temp-file cleanup.
- [ ] A command-agnostic script-session module owns script deduction,
      resolution, task/skill environment construction, secret injection,
      subprocess execution, and its exit result. It does not advance a step,
      mark a task done, post lifecycle notifications, or call Typer exits.
- [ ] A launch service interprets one ticket's durable workflow generically:
      it chooses agent versus script from ticket/skill files, runs the current
      step, re-reads the ticket, and chains only while file-backed status,
      step, and assignee state say to continue. It contains no workflow name,
      skill ref, or bootstrap target name as execution policy.
- [ ] Existing callers (`launch`, `ticket`, and `megalaunch`) use the
      extracted single-agent session path; no compatibility import shim remains
      in `commands/launch.py`.
- [ ] Current lifecycle behavior is preserved but visibly isolated in the
      launch service: draft/paused/blocked activation, `active -> in_progress`,
      unresolved-blocker re-block, and successful-script step/done writes.
      The ticket records these as the handoff boundary to
      `v1/microkernel/10-lifecycle-verbs-to-ticket-operations` rather than
      declaring the writes executor substrate.
- [ ] Launch still fails loud, before unsafe mutation where applicable, for an
      unknown target, missing context/skill/script, missing agent/TTY, unresolved
      declared secret, blocked/done or human-handoff state, agent/script non-zero
      exits, and lifecycle validation failures. Git/sync failures remain visible
      through their existing state-writer/refresh paths.
- [ ] No lock abstraction is introduced. The existing task-scoped
      `COGA_DONE_SENTINEL` PTY channel remains agent-process substrate, while
      expected-task/expected-step guards remain part of lifecycle coordination.
- [ ] Focused launch, script, restart, ticket, and megalaunch tests pass;
      the full pytest suite, `git diff --check`, and
      `coga validate --task v1/microkernel/03-launch-decomposition --json`
      pass.
- [ ] `coga/launch`, `coga/script-tickets`, `coga-dev/internals/agent-spawn`,
      `coga-dev/codebase`, `coga-dev/microkernel`, and
      `docs/archive/cli-extension-audit.md` describe the new source boundary. Any
      changed shipped context is updated in both the live and packaged copies.

##### Proposed shape

###### Responsibility classification

**Executor substrate that stays in Python**

- Compose a prompt from the resolved target and current ticket files, write the
  temporary prompt file, and use the existing file-pointer fallback when one
  argv element would exceed Linux's limit.
- Resolve the configured agent, build its argv, inject only ticket-declared
  secrets, spawn under the PTY watcher, scope the done sentinel to the task,
  return a typed exit/termination result, and capture/redact usage.
- Deduce agent versus script from the current ticket/skill files; resolve and
  execute a skill-backed or ticket-owned script with the documented `COGA_*`
  environment and return its exit result.
- Re-read durable ticket state after a session and generically interpret the
  current workflow's step, assignee, and script declaration. The loop is an
  interpreter for file-backed policy, not policy of its own.
- Support stateless bootstrap targets without inventing lifecycle state. The
  generic distinction is `BootstrapRef` versus `TaskRef`, never a list of named
  bootstrap tickets in the substrate.

**Launch policy/orchestration outside the substrate**

- Git push-auth preflight, installed-versus-source warnings, and generated
  agent-skill-view refresh are start-of-run policy/diagnostics. Keep their
  current behavior during the extraction, but keep them above the executor
  boundary. Their removal or relocation belongs to
  `v1/microkernel/07-support-commands-boundary` and the point-of-use
  git/open-PR paths, not `agent_session` or `script_session`.
- Prompt-report rendering is a read-only compose diagnostic. Keep the existing
  flag as a thin early-return in this PR, and hand its eventual surface to
  `v1/microkernel/06-read-report-commands-as-ticket-workflows`.
- Recurring/megalaunch idle and wall-clock defaults, timeout classification,
  and repeated-task selection are caller policy. The session runner accepts
  concrete limits, but choosing them belongs to
  `v1/microkernel/09-work-orchestration-commands-to-tickets`.

**Lifecycle transition boundary**

- `_auto_activate`, `mark_in_progress`, blocked-resume re-blocking, and the
  successful-script calls to `advance_step`/`mark_done` stay behaviorally
  intact in the launch service for this PR, grouped together and kept out of
  both low-level session modules.
- `COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`, and `COGA_SUPERVISED` remain the
  generic handoff contract between the supervisor and lifecycle writes. The
  sibling lifecycle ticket decides how user-facing `mark`/`bump`/`block`/
  `unblock` surfaces change without reopening process execution.

**Compatibility sugar and small wrappers**

- `--agent` remains an ephemeral executor selection and never rewrites ticket
  ownership or crosses a human handoff.
- Discussion/kickoff behavior remains an explicit option of the one-session
  runner for `ticket`/`project`; named `bootstrap/orient` and
  `bootstrap/ticket` knowledge must stay in the thin caller/compatibility layer,
  not the executor. Default-alias cleanup belongs to
  `v1/microkernel/08-residual-command-surfaces`.
- Preserve `--prompt-report`, `--idle-timeout`, `--max-session`, and the hidden
  timeout-return behavior during the structural PR so recurring callers do not
  change accidentally. Their classification above prevents the new substrate
  API from treating those CLI choices as permanent core concepts.

###### Source changes

1. Add `src/coga/agent_session.py`. Move `AgentSessionResult`, agent argv and
   discussion-template construction, oversized-prompt argv handling,
   `spawn_agent_session`, usage/redaction helpers, and their constants here.
   Keep the existing keyword-driven caller differences; do not add a plugin or
   callback framework.
2. Add `src/coga/script_session.py`. Move script-mode deduction, script/env/argv
   resolution, inline-script temp handling, and the raw subprocess run here.
   Return a small result value instead of posting, mutating a ticket, or
   exiting. Preserve the exact resolution order: current single script-backed
   step skill, then ticket-owned script.
3. Add `src/coga/launch.py` as the reusable ticket supervisor. Move target
   eligibility, generic workflow chaining, per-step agent rotation, fail-loud
   preflights, checkout refresh, and the grouped lifecycle adapter calls here.
   It composes the two session modules but does not parse Typer values.
4. Reduce `src/coga/commands/launch.py` to the CLI head and prompt-report
   presentation. Convert service/session failures to one typed `LaunchError`
   path so library code no longer calls `_bail` or `sys.exit`; propagate real
   child exit codes at the command boundary.
5. Update `commands/ticket.py` and `megalaunch.py` to
   import the public one-session API from `coga.agent_session`. Update recurring
   in-process callers to invoke the launch service rather than calling the
   Typer function with `OptionInfo`-sensitive defaults.
6. Split tests by boundary: agent argv/spawn/usage cases move to
   `tests/test_agent_session.py`; raw script resolution/execution cases move to
   `tests/test_script_session.py`; `tests/test_launch.py` and
   `tests/test_launch_restart.py` retain end-to-end status, handoff, chaining,
   blocked-resume, timeout, and refresh contracts. Update monkeypatch targets
   rather than keeping old import aliases.
7. Update durable architecture/source docs and both live/package copies where
   applicable. State explicitly that the core exception is the executor plus
   its trust/process hooks; lifecycle and caller policy are dependencies used
   by launch today, not permanent user-facing core commands.

##### Out of scope

- Moving or redesigning `create`, `skill *`, secret acquisition, prompt
  composition order, the PTY watcher protocol, usage-log schema, or git sync
  internals.
- Implementing the lifecycle-verb migration, changing status/step semantics,
  or replacing `mark`/`bump`/`block`/`unblock`; that is the lifecycle sibling.
- Moving `retire`, `megalaunch`, recurring scans, read/report
  commands, aliases, or support commands to tickets. This ticket only gives
  those migrations a stable executor API and records their owning sibling.
- Adding transient launch parameters, a launch plugin API, a policy registry,
  a filesystem lock, a daemon, or a second workflow representation.
- Combining the structural extraction with policy removals or compatibility
  breaks. Once the extraction lands, each owning sibling can delete its policy
  from the launch layer without editing process-execution code.

Previous ref: `microkernel/launch-decomposition` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.

#### Design findings

- `src/coga/commands/launch.py` currently mixes three layers: a shared
  single-agent session runner, deterministic ticket/workflow supervision, and
  Typer/user-facing policy. `coga ticket` and `coga megalaunch` import the
  session runner back out of the command module, which
  is the clearest existing seam.
- The irreducible bootstrap exception is execution, not every behavior that
  happens to run before or after it: a ticket cannot execute the ticket that
  implements ticket execution. The `coga launch <target>` head therefore stays
  as a thin addressable entrypoint over Python substrate even though `create`
  remains the only command presumed core by the directory-level rule.
- Current Coga has no launch mutex or lock to preserve. The relevant executor
  mechanisms are the PTY watcher plus task-scoped done sentinel; the expected
  task/step environment values are lifecycle compare-and-swap guards owned by
  the lifecycle boundary.
- Status activation, `active -> in_progress`, blocked-ticket resume/re-block,
  and script success advancing/finishing are lifecycle behavior. Their eventual
  command-surface migration belongs to
  `microkernel/lifecycle-verbs-to-ticket-operations`, not this
  extraction.
- Git push readiness, installed/source skew warnings, generated agent-skill
  view refresh, prompt-report rendering, and recurring liveness defaults are
  launch-adjacent policy or diagnostics, not executor substrate. Existing
  sibling tickets provide their follow-up homes; this ticket should expose the
  seam without folding those policies into the executor.

#### Open Questions

None. The owner review should confirm the deliberately behavior-preserving
first PR and the follow-up ownership recorded in the spec.

#### Premise check (2026-10-16, pull-forward to v1)

- Subject exists and is undelivered (Dream W39 F53): no
  `src/coga/agent_session.py`, `script_session.py` or `src/coga/launch.py`.
- Surfaces drifted since the design: `commands/launch.py` grew from 1,179 to
  3,782 lines; `launch_script.py` moved to `src/coga/` (600 lines); `coga
  project` was removed. Paths, line counts and the `project` caller were
  corrected in the body; the headings were demoted so the criteria and
  proposed shape compose.
- **Not re-verified:** the responsibility inventory in "Proposed shape" was
  written against the 1,179-line file, which has roughly tripled since, and
  `commands/retire.py` and `recurring_runner.py` now also import from
  `commands/launch.py` (callers today: `cli`, `ticket`, `retire`,
  `megalaunch` (both modules), `recurring_runner`). Owner
  decision at `review-design`: approve with the implementer re-inventorying
  as its first task, or send it back to `design` for a fresh inventory.
  Recommended: send back; the classification is the deliverable that the
  five sibling tickets rely on.
- Status is still `paused` from the 2026-07-27 park; resume with
  `coga mark active` when ready.

#### Design-step verification

- Read the live ticket, `docs/vision.md`, the composed Coga contexts,
  `src/coga/commands/launch.py`, `commands/launch_script.py`, `compose.py`,
  `repl_supervisor.py`, lifecycle modules, shared callers, launch tests, and the
  command-cleanup sibling tickets.
- `git diff --check` passed.
- `PYTHONPATH=/home/n/Code/claude/coga/src python3.12 -m coga.cli validate
  --task microkernel/launch-decomposition --json` passed: 1 task OK,
  no issues.

### 2026-11-12 — Prompt assembly before the experimental split

Superseded by: the numbered `03-prompt-assembly/` group for prompt preparation,
paired comparison and evidence-gated implementation; the narrowed execution
scope above retains the original ticket's remaining deliverable.
Reason: the owner required proving that a new assembler is better before
replacement, and requested a numbered group rather than one broad ticket.
The following scope and evaluation are retained as history, not dependencies
or permission to implement.

#### Description

Finish separating the generic ticket executor from the procedures that use
it. The CLI/service split already shipped; the remaining work is in
`src/coga/launch.py`, its consumers, and the boundary between stateless command
tickets and stateful workflow execution. This includes how every agent launch
builds its prompt, not just guided ticket authoring. First compare concrete
prompt forms at representative stages, then implement the selected form. This
is the 2026-11-12 scope proposal for owner review, not approval to resume the
paused implementation.

##### Objectives advanced

Ticket ownership: callers should own their procedure and defaults. Hackability:
a customized ticket must use the same executor without adding a core case.
Simplification: remove duplicated preparation and command-specific branches;
a module split alone does not complete this ticket.

##### Owner direction — general prompt assembly

The ticket is the common unit of work for deterministic code and agent work.
For an agent phase, assemble the requested skills, context blocks, relevant
workflow fragment, and the ticket's own intent and working state around a
minimal base prompt. The base carries only the shared instructions and
runtime additions needed for that invocation. Procedures belong with their
tickets, skills and workflows, so customizing those files changes what runs
without adding a named case to the executor.

Apply this model wherever Coga builds an agent prompt: ordinary workflow
steps, stateless command tickets, guided authoring, megalaunch and recurring
agent sessions. A deterministic phase still executes code through the same
ticket execution model; it does not become an agent prompt or require an
agent merely to use the common mechanism.

Do not choose a final prompt layout by intuition alone. Before runtime
implementation, put complete candidate prompts in this ticket (or sibling
attachments if needed), showing the assembled result at representative
stages. Compare the current form with minimal-base alternatives, test them
with agents on bounded representative tasks, and record the observed behavior
and tradeoffs. Inspectability and correct behavior matter alongside size.
Record which base instructions and runtime additions survive and why; the
exact layout and additions remain design questions until this comparison.

Include at least an ordinary workflow step, guided editing of an existing
ticket, and a stateless agent procedure. Cover attended versus queued conduct,
an owner assist, and a script-to-agent handoff where their required material
differs. Each example must make the ticket, requested skill, relevant context
blocks and workflow instructions identifiable. Verify which instructions
actually apply to that session, including its completion and checkout rules.
Do not copy incompatible procedure rules into a universal base.
Use representative agent trials, not an exhaustive cross-product of all
callers and postures; regression tests cover each caller's assembly contract.

##### Premise check against main

Snapshot: `49b34b229` (2026-11-12); physical line counts include blanks and
comments, exclude tests/docs, and describe inventory rather than promised savings.

1. The subject exists: the large shared runtime remains.
2. The old path and API inventory drifted. `commands/launch.py` is now a
   100-line adapter; `launch.py` is the 4,577-line service. `launch_script.py`
   is 620 lines. `agent_session.py` and `script_session.py` do not exist.
3. The prior plan is retained under Superseded designs. Its substance is
   restated here; retired tickets and archived audit pages are not dependencies.
4. Part shipped in `b3007ef2e`: the plain Python launch API, result/error
   boundary and thin Typer adapter. Drop that extraction from remaining work.
   Production callers now import `coga.launch`, not `commands.launch`.

##### Current responsibility inventory

| Surface | Current responsibility | Proposed boundary |
| --- | --- | --- |
| `launch.launch`, `_LaunchInvocation`, `LaunchResult`, `LaunchBail` | Target admission, preparation, workflow chaining, refresh and outcomes | Generic supervisor; preserve the public seam rather than creating a second launch service |
| `spawn_agent_session`, `AgentSessionResult`, `build_agent_command`, command representability and usage helpers | One composed agent process; shared with authoring and megalaunch | Proposed session-module boundary, subject to prompt-comparison findings; migrate real callers together if extracted |
| `launch_script.script_entry_point`, `run_script_phase`, `run_script_chain` | Exact `ticket.py` classifier, execution, refresh and handoff | Keep the existing classifier; split raw execution only if it removes duplication or lifecycle coupling |
| `compose.compose_prompt_report`, prompt resources, workflow/skill layers, `commands.ticket._authoring_ticket` | Shared prompt assembly plus an authoring projection that still inherits ordinary execution instructions | One general assembly mechanism using the ticket and applicable procedure blocks, with a minimal base selected after prompt trials |
| `checkout_policy.select_checkout_policy` (145 lines), `checkouts.py` (1,159 lines) | Select policy from shipped names/instruction equality; perform shared Git mechanics | The dedicated checkout-policy ticket owns declaration and compatibility; this ticket consumes its result |
| `DISCUSSION_BOOTSTRAP_TICKETS`, `_bootstrap_kickoff`, direct-chat and onboarding cases | Named procedure defaults and special behavior | Move defaults to their owning ticket/caller where possible; retain the actual chat lock/receipt and admission guarantees in shared machinery |
| `launch_recurring_period`, `launch_with_before_spawn`, `settle_delegated_period` | Recurring leases, publication and held-child admission | Keep explicit typed contracts; queue selection and scheduling remain caller policy |
| `_format_prompt_report`, push-auth preflight, agent skill-view refresh | Diagnostics and execution readiness | Reports belong to the read/report sibling; support classification belongs to the support sibling; required point-of-use checks remain enforced |

Callers to migrate together with any session extraction: `commands/ticket.py`,
both megalaunch modules, `recurring_runner.py`, and the packaged
`bootstrap/retire/ticket.py`. `cli.py` also consumes `checkout_guard_scope`.
Several callers still use private service helpers; eliminate those dependencies
through the existing shared operations, not forwarding imports in command files.

##### Proposed changes and contracts

1. Retain one generic supervisor and expose the one-session executor already
   shared by real callers. Reduce its caller-specific setup only where the
   callers can converge without losing their admission/publication semantics.
   Choose module boundaries after the prompt comparison; a session extraction
   is a proposed means, not a prerequisite for testing or an end in itself.
   No plugin host, phase registry, or new callback framework.
2. Establish the minimal stateless command-ticket execution contract needed
   by the read/report and customization tickets. Today `launch` loads a user
   config and its CLI exit normally sweeps state; a read command currently
   needs neither publication nor a configured user. A blind alias therefore
   changes behavior. Design explicit generic invocation policy for this
   distinction, with no command-name allowlist, before migrating those heads.
   Source inspection/help must remain usable with dirty state, no agent/TTY,
   and no Git writes. A write command retains its publication boundary.
3. Coordinate the narrow completion seam with lifecycle and orchestration.
   Script launch clears the outer supervisor/expected-task environment. A
   nested command ticket cannot silently become `block`, `bump`, or a
   bootstrap-completing `slack` call. Preserve the existing completion
   primitives until a reviewed equivalent proves identity and termination.
4. Keep stateful script behavior intact: a script completes its own step
   through the lifecycle CLI; exit zero alone never advances or finishes it.
   An unchanged open step falls through to the agent. Skills never supply
   executable launch plugins, inline scripts, or a static script/agent flag.
5. Implement the tested prompt form through shared composition, with every
   agent-spawn caller using it. Resolve applicability before assembly rather
   than stacking instructions that contradict each other. Keep source paths
   and per-block reporting inspectable, and preserve failures for required
   missing skills or contexts. Move procedure-specific instructions out of
   the base only when their owning ticket, skill or workflow supplies them.
6. Preserve native Windows console/Job Object behavior, POSIX supervision,
   environment isolation, secret injection/redaction, startup publication,
   assist receipts, recurring leases and released launch claims. The old
   "no locks exist" inventory is obsolete: direct chat has a checkout guard.

##### Acceptance and reduction evidence

- [ ] Concrete candidate prompts, bounded agent-trial results and the chosen
      form are recorded before runtime implementation. The examples cover
      the session shapes above and explain the minimal base's additions.
- [ ] Every agent-launch path uses the general assembly mechanism. The ticket,
      requested skills, context blocks and relevant workflow material are
      present without contradictory completion or checkout instructions.
- [ ] Composition regressions cover applicability as well as inclusion:
      authoring never receives instructions to execute or advance the target
      workflow, stateless work never inherits a task lifecycle, and stateful
      execution retains its required completion and handoff contract.
- [ ] Thin command adapter remains thin; no duplicate public launch API or
      compatibility re-export is added.
- [ ] Caller policy is editable beside its ticket where selected by design;
      each retained named special case has its concrete invariant recorded.
- [ ] Read-only stateless dispatch and write dispatch have explicit, tested
      config, stream, exit, publication and checkout behavior.
- [ ] At least one real dependency/duplicate path is removed; report the
      whole-system evidence required by `coga-dev/microkernel/objectives`.
- [ ] Existing launch, restart, script, authoring, megalaunch, recurring,
      environment and supervisor tests exercise the moved boundaries. Use the
      full-suite and native Windows receipts required by `coga-dev/testing`.
- [ ] Update `coga/launch`, `coga/script-tickets`, the checkouts/publication
      owners, `coga/prompt-composition`, affected prompt/skill/workflow owners
      and local source map where their contracts actually change.

#### Context

The owning scope is this ticket; workflow checkout declaration belongs solely
to `declare-each-workflow-step-s-checkout-policy-in-th`. Its implementation can
precede the session extraction. Read/report and customization depend only on
the stateless contract they need; recipe job moves need no new session API.

The new prompt comparison, agent trials and choice of form are outstanding
design work. Keep the current owner `review-design` gate until the owner has
reviewed those artifacts and selected the form; approving this scope alone
does not approve runtime implementation. Preserve the paused status, current
step and frozen workflow during authoring.

Observed prompt failure during this authoring session: the normal ticket loop
instructs the agent to run `coga bump`, while the requested `bootstrap/ticket`
skill forbids advancing the edited ticket. `commands.ticket._authoring_ticket`
replaces skills and removes the current step in memory, but
`compose.compose_prompt_report` still adds the task execution loop for a
`TaskRef`. Fix the general applicability boundary, rather than adding another
instruction that asks the agent to override an earlier one.

Prompt-assembly sources are `src/coga/compose.py` (`compose_prompt_report`,
`_skill_layers`, `_step_layers`), `src/coga/commands/ticket.py`
(`_authoring_ticket`, `_run_authoring_session`), and `src/coga/resources/prompt*.md`.
The current composition contract is cited rather than attached:
`coga/prompt-composition` at
`src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md`;
read "Layer order", "What each layer reads", and "Blocker preamble versus
authoring" before comparing candidate forms. It currently selects one conduct
resource, reads attached skills and contexts whole, and omits a skilled step's
inline workflow section. The new design must explicitly decide how the
relevant workflow fragment and skill fit together without duplication.

The following editing targets are cited rather than attached; read their
named sections before designing changes and update their owners in the same
implementation PR:

- `coga/launch`,
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md`:
  "Phases and routing", "Agent preflight order", "The step chain", and
  "Options and exits". Agent readiness checks must still precede startup
  writes; a stateless target never acquires workflow chaining.
- `coga/script-tickets`,
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md`:
  "One deterministic phase", "Chaining", and "COGA_TASK_* contract".
  `launch_script.run_script_phase` precedes agent preparation, exit zero does
  not advance a stateful step, and script children must not inherit authority
  to terminate an outer supervised session.
- `coga-dev/internals/agent-spawn`,
  `docs/contexts/coga-dev/internals/agent-spawn/SKILL.md`: "Launch API and
  phases", "Order inside one call", "Per-caller parameters", "Large prompts",
  and "The supervisor". `spawn_agent_session` owns one session; its callers
  have distinct admission and publication contracts. Preserve command-line
  representability checks before effects and the supervisor's completion
  channel when moving composition or session code.
- `coga-dev/codebase`, `docs/contexts/coga-dev/codebase/SKILL.md`: "Source map"
  and "Contribution rules". Migrate real callers with a shared extraction;
  update the source map instead of leaving a second API in a command module.
- `coga/checkouts`,
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md`:
  "Start, work, end" and "Which checkout you invoke Coga from". Shared
  checkout mechanics and truthful runtime notices remain required; the
  checkout-policy sibling owns replacement of the hidden policy table.
- `coga/state-publication`,
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`:
  "When Coga publishes", "Control versus feature checkouts", and "Prepared
  ticket transactions". Preserve write transactions and held knowledge while
  making read-only stateless dispatch free of publication effects.

For publication implementation, cite rather than attach
`coga-dev/internals/state-publication` at
`docs/contexts/coga-dev/internals/state-publication/SKILL.md`: read
"Invariants", "The end-of-command sweep", and "Guided-authoring
finalization", plus "Ordinary managed startup" in its `publish/SKILL.md`
leaf. `cli._should_sweep_coga_state` currently selects sweeping command heads;
moving a read command under launch must not silently enable that sweep.
`authoring.finalize_authored` validates changed tickets and publishes their
required knowledge together; a refusal withholds the general sweep.
`launch._publish_startup` groups ordinary managed startup before checkout
entry. Use the linked user `state-publication/launch-boundaries/SKILL.md`
classification and the implementation `log-writers/SKILL.md` inventory when
changing any caller's publication order.

Drop the already-shipped Typer/service split, removed `project` caller,
skill-backed script resolution, automatic script completion, duplicate live
definitions and archive-audit editing from this implementation scope. Defer
cosmetic file splits and broad renames that advance none of the objectives.

#### Independent evaluation before the split

Verdict : le ticket est prêt pour des expériences de prompt bornées. Il n’est pas prêt pour l’implémentation : les candidats, les essais et le choix du propriétaire restent explicitement à produire au gate `review-design`, sans modifier le statut `paused`, l’étape ou le workflow gelé.

L’ensemble est cohérent avec le microkernel. Le ticket demande un résultat observable, rend l’extraction de session conditionnelle aux résultats et conserve les garanties de `ticket.py`. Le défaut d’authoring est confirmé : `commands.ticket._authoring_ticket` retire l’étape, mais `compose.compose_prompt_report` ajoute encore `prompt-ticket.md` à tout `TaskRef`. La séparation entre instructions applicables et simple inclusion est donc un vrai besoin.

Un point de périmètre doit être tranché avant de figer le contrat « toutes les voies » : `recurring_autofix.build_prompt` et `recurring_autofix.analyze_record` construisent et exécutent aussi un prompt agent, hors de `compose` et de `spawn_agent_session`. La section « Owner direction — general prompt assembly » et l’acceptation « Every agent-launch path » les englobent littéralement, mais l’inventaire ne les mentionne pas. Préciser leur inclusion, leur coordination avec un sibling, ou leur exclusion motivée. Cela ne bloque pas les premiers essais représentatifs.

Pour choisir la meilleure forme, les objectifs annoncés — comportement correct, inspectabilité, taille — suffisent à commencer la conception. Avant les essais, consigner cependant un protocole commun : mêmes tâches et entrées pour chaque candidat, instructions attendues ou interdites, résultats observés et limites. Les erreurs de completion, de checkout ou d’autorité doivent éliminer un candidat ; le gain de taille vient ensuite. Les essais agents et les régressions de composition apportent des preuves différentes.

Deux précautions de conception restent utiles :

- « Resolve applicability before assembly » ne doit pas devenir un moteur qui devine la procédure depuis les noms de skills, le texte ou le workflow. Préférer des faits explicites fournis par l’invocation, avec leur provenance visible.
- Comparer réellement les étapes avec skills et les étapes inline. `compose._step_layers` choisit actuellement l’un ou l’autre ; composer systématiquement les deux pourrait introduire duplication et contradiction. Le ticket laisse correctement ce choix ouvert.

Les citations et lectures de publication sont maintenant précises ; les principaux sujets susceptibles d’être édités ne sont plus attachés. Aucun besoin évident d’attachement supplémentaire. Le périmètre est large, mais reste acceptable pour cette phase de comparaison ; décider des éventuels siblings d’implémentation après le choix du contrat.

Dans le rapport fourni, aucune couche ne dépasse environ 40 %. La plus grande représente 23,6 % pour `coga-dev/testing` en owner review et 24,0 % pour `bootstrap/ticket` en authoring. Les contextes attachés représentent respectivement environ 65 % et 50 % du total : à réexaminer pendant les comparaisons, sans suppression mécanique. Le blackboard ne nécessite pas de réduction. Les chiffres précèdent les dernières modifications documentaires ; mesurer les candidats complets à leur révision d’essai.

## Recipe Failure

Recipe: `publish-state`
Exit: 2
Task: `v1/microkernel/03-launch-decomposition`
Recorded: 2026-11-13T05:32:23+00:00

    publish-state: /home/n/Code/coga/coga/tasks/v1/microkernel/03-prompt-assembly/01-define-prompt-candidates-and-trial-protocol.md is not a regular file

Resolved: the strict recipe accepts existing regular files as required paths, not deleted files. Retried with the six current files; publication succeeded at `ea76d6734fc9508a89e1ea7bba95ee1645abb6d7`. Verified that both former file-form copies are absent from `origin/main` and only the intended three grouped tickets plus README remain. The checkout is clean on main; no launch or workflow transition occurred.
