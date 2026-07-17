---
slug: cleanup-core-commands/launch-decomposition
title: Decompose launch into substrate plus ticket orchestration
status: in_progress
owner: nicktoper
human: nicktoper
agent: codex
assignee: nicktoper
contexts:
- coga/principles
- coga/architecture
- coga/codebase
- coga/current-direction
- coga/extension-model
- coga/project-stage
- coga/cli
- dev/code
skills: []
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
secrets: null
script: null
step: 2 (review-design)
---

## Description

`src/coga/commands/launch.py` is currently both the `coga launch` Typer command
and the shared runtime used by task launches, `coga ticket`, `coga project`, and
`coga megalaunch`. Its 1,179 lines combine target/status policy, workflow
supervision, prompt/agent process execution, usage capture, git readiness and
refresh behavior, and lifecycle writes. Script execution adds another 460
lines in `commands/launch_script.py`, including both subprocess mechanics and
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

## Context

Directory index: `cleanup-core-commands/README`.

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

## Acceptance Criteria

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
- [ ] Existing callers (`launch`, `ticket`, `project`, and `megalaunch`) use the
      extracted single-agent session path; no compatibility import shim remains
      in `commands/launch.py`.
- [ ] Current lifecycle behavior is preserved but visibly isolated in the
      launch service: draft/paused/blocked activation, `active -> in_progress`,
      unresolved-blocker re-block, and successful-script step/done writes.
      The ticket records these as the handoff boundary to
      `cleanup-core-commands/lifecycle-verbs-to-ticket-operations` rather than
      declaring the writes executor substrate.
- [ ] Launch still fails loud, before unsafe mutation where applicable, for an
      unknown target, missing context/skill/script, missing agent/TTY, unresolved
      declared secret, blocked/done or human-handoff state, agent/script non-zero
      exits, and lifecycle validation failures. Git/sync failures remain visible
      through their existing state-writer/refresh paths.
- [ ] No lock abstraction is introduced. The existing task-scoped
      `COGA_DONE_SENTINEL` PTY channel remains agent-process substrate, while
      expected-task/expected-step guards remain part of lifecycle coordination.
- [ ] Focused launch, script, restart, ticket, project, and megalaunch tests pass;
      the full pytest suite, `git diff --check`, and
      `coga validate --task cleanup-core-commands/launch-decomposition --json`
      pass.
- [ ] `coga/architecture`, `coga/codebase`, `coga/extension-model`, and
      `docs/cli-extension-audit.md` describe the new source boundary. Any
      changed shipped context is updated in both the live and packaged copies.

## Proposed Shape

### Responsibility classification

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
  `cleanup-core-commands/support-commands-boundary` and the point-of-use
  git/open-PR paths, not `agent_session` or `script_session`.
- Prompt-report rendering is a read-only compose diagnostic. Keep the existing
  flag as a thin early-return in this PR, and hand its eventual surface to
  `cleanup-core-commands/read-report-commands-as-ticket-workflows`.
- Recurring/megalaunch idle and wall-clock defaults, timeout classification,
  and repeated-task selection are caller policy. The session runner accepts
  concrete limits, but choosing them belongs to
  `cleanup-core-commands/work-orchestration-commands-to-tickets`.

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
  `cleanup-core-commands/residual-command-surfaces`.
- Preserve `--prompt-report`, `--idle-timeout`, `--max-session`, and the hidden
  timeout-return behavior during the structural PR so recurring callers do not
  change accidentally. Their classification above prevents the new substrate
  API from treating those CLI choices as permanent core concepts.

### Source changes

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
5. Update `commands/ticket.py`, `commands/project.py`, and `megalaunch.py` to
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

## Out of Scope

- Moving or redesigning `create`, `skill *`, secret acquisition, prompt
  composition order, the PTY watcher protocol, usage-log schema, or git sync
  internals.
- Implementing the lifecycle-verb migration, changing status/step semantics,
  or replacing `mark`/`bump`/`block`/`unblock`; that is the lifecycle sibling.
- Moving `project`, `retire`, `megalaunch`, recurring scans, read/report
  commands, aliases, or support commands to tickets. This ticket only gives
  those migrations a stable executor API and records their owning sibling.
- Adding transient launch parameters, a launch plugin API, a policy registry,
  a filesystem lock, a daemon, or a second workflow representation.
- Combining the structural extraction with policy removals or compatibility
  breaks. Once the extraction lands, each owning sibling can delete its policy
  from the launch layer without editing process-execution code.

<!-- coga:blackboard -->

Created under `cleanup-core-commands/` as part of the command-surface breakdown.

## Design findings

- `src/coga/commands/launch.py` currently mixes three layers: a shared
  single-agent session runner, deterministic ticket/workflow supervision, and
  Typer/user-facing policy. `coga ticket`, `coga project`, and `coga
  megalaunch` import the session runner back out of the command module, which
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
  `cleanup-core-commands/lifecycle-verbs-to-ticket-operations`, not this
  extraction.
- Git push readiness, installed/source skew warnings, generated agent-skill
  view refresh, prompt-report rendering, and recurring liveness defaults are
  launch-adjacent policy or diagnostics, not executor substrate. Existing
  sibling tickets provide their follow-up homes; this ticket should expose the
  seam without folding those policies into the executor.

## Open Questions

None. The owner review should confirm the deliberately behavior-preserving
first PR and the follow-up ownership recorded in the spec.

## Design-step verification

- Read the live ticket, `docs/vision.md`, the composed Coga contexts,
  `src/coga/commands/launch.py`, `commands/launch_script.py`, `compose.py`,
  `repl_supervisor.py`, lifecycle modules, shared callers, launch tests, and the
  command-cleanup sibling tickets.
- `git diff --check` passed.
- `PYTHONPATH=/home/n/Code/claude/coga/src python3.12 -m coga.cli validate
  --task cleanup-core-commands/launch-decomposition --json` passed: 1 task OK,
  no issues.
