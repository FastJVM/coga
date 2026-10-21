---
name: coga/launch
description: What `coga launch <target>` accepts, the checkout boundary around each ticket launch, how status and routing decide what runs, the preflight order before any lifecycle write, the step-chaining supervisor's stop rules, and the `--agent`, `--prompt-report`, and liveness options.
---

# Coga launch

`coga launch <target> [args...]` starts or resumes work on one target. It is
the attended path: a human typed it. Queue draining is `coga megalaunch`
([megalaunch](../megalaunch/SKILL.md)); scheduled work is `coga recurring`.

The CLI adapter (`src/coga/commands/launch.py`) owns Typer arguments, presentation
and process exits. Python callers use `coga.launch`: ordinary parameter defaults,
`LaunchResult(kind, exit_code)` for a completed launch, and `LaunchBail(code,
reason)` for a refusal or propagated failure. `LaunchBail` is an ordinary
exception, never `SystemExit`. Progress goes through the scoped
`launch_reporting` callback (plain stdout/stderr by default); callers can render
it independently of the result. The recurring entry point also returns its
child-generation lease, and delegation retains the actual session exit code.
Signals unwind library handlers before that public boundary translates them
into `LaunchBail`; recoverable exception handlers must not swallow termination.
Internal callers must not invoke the Typer command function.

`_launch` coordinates one `_LaunchInvocation` through five fixed phases:
target preparation, assist alignment and ticket classification, initial script
execution, agent preflight, and step supervision. Each phase can return a
completed result before the next begins. Mutable config, target, routing and
blocker state belong to that invocation; checkout return and blocker cleanup
read its latest state after synchronization. This is internal organization,
not a phase registry or extension surface. The ordering guarantees below still
apply across those boundaries.

## Targets

- A task by any unique prefix of its ref. A nested task is its path under
  `tasks/` (`marketing/coga-crm`), exactly as `coga status` prints it.
- `bootstrap/<name>` — a stateless target: no lifecycle or chaining.
  Its launch log line publishes immediately; sessions in one checkout still
  share its branch and files.
  `coga chat` is the default alias for `launch bootstrap/orient`.
- A `recurring/<name>` period is gated first (control branch, owner,
  verified control catch-up, exit 75 when stale) and a frozen `delegate:`
  period routes straight to its bootstrap target; see
  `coga/recurring/delegation` and `coga/internals/recurring-admission`.

Trailing positional arguments reach an agent prompt as an ordered JSON
`## Launch arguments` block, and a bootstrap `ticket.py` as its argv. A
stateful `ticket.py` target refuses them
([script tickets](../script-tickets/SKILL.md)).

## Checkout boundary

An ordinary task launch and direct `bootstrap/orient` (`coga chat`) run from a
clean, current control checkout. Orientation prepares before even resolving
its bootstrap target, so a repo-local override is read from current control.
Direct chats in one Git checkout are serialized by a nonblocking occupancy
guard; a second chat refuses before publishing or preparing anything. Its
scope and lifetime are owned by
[dev/checkouts/launch-boundary](../../dev/checkouts/launch-boundary/SKILL.md).
For ordinary tasks, target
resolution and the recorded-checkout test only classify; then launch
publishes Coga state (the sweep over the Coga roots) and prepares the
invoking checkout (`git.prepare_control_checkout`) before the delegation
read, recorded-assist alignment, script discovery, activation, the
agent-skill view, or prompt composition. It then reloads config (a changed Git destination refuses
with 75) and re-resolves the same canonical ref. It never selects a
different prefix match. A spelling that does not resolve locally, and is not
`bootstrap/` or `recurring/`, is resolved again after preparation, so a
ticket created on control after the checkout's branch point launches.

The same publish-then-prepare runs after every started agent session and
every `ticket.py` phase (inside `run_script_chain`), before the next chain
decision, and on every exit path. Routing, secrets, script paths, and prompts
come from the refreshed files; a target gone from control ends the chain. The
session receives `COGA_LAUNCH_RETURNS_CHECKOUT=1`. Entry refusal exits 75
with no work started. A later refusal warns, preserves the remaining work and
the session's exit, stops chaining, and withholds the end-of-command sweep.
Recurring periods keep their own entry gates and get only the return half,
in the checkout the runner selected, delegated periods included; a refused
return there exits 75 so the sweep stops instead of pausing the period and
launching the next.
The procedure, proof rules, refusal recovery, and exemptions (other bootstrap
targets and delegated bootstrap sessions,
`--prompt-report`, Git-disabled, non-Git, or
remote-less workspaces, the recorded assist or sandbox-clone checkout, a
released megalaunch witness) are owned by
[dev/checkouts/launch-boundary](../../dev/checkouts/launch-boundary/SKILL.md). Exempt launches keep the
teardown refresh below.

Inside an ordinary task launch whose entry prepared control, each agent
step's checkout is then prepared from its frozen step: after activation and
the start publication, launch selects the step's entry policy, creates or
reuses and publishes the recorded branch where the policy names one, and
composes the prompt from control state; only then does it publish its
`launched` audit line on control (a refused preparation records no launch),
re-prove control (recomposing if the ticket gained notes), switch, project
the ticket, and spawn with that exact prompt
(`spawn_agent_session(composed_prompt=...)`). The policy table, refusals, and
recovery are owned by [dev/checkouts](../../dev/checkouts/SKILL.md);
`ticket.py` phases run first and are never moved to a feature branch, and
recurring, delegated, caller-guarded, recorded-checkout, and megalaunch
spawns keep their own paths with no branch setup. Every composed prompt ends
with a runtime **Checkout (runtime)** notice of what launch observed and who
returns the checkout ([prompt composition](../prompt-composition/SKILL.md)).

## Status is the signal

There is no task-ownership mutex: `status` says whether someone is working.
Launch accepts `active` and `in_progress` directly (an `in_progress` resume
does not flip status again). Launching `draft` or `paused` *is* the readiness
decision: activation runs inline with the same refusals as `coga mark active`
(no workflow, unfreezable `workflow:`, empty required extension field,
unsynthesized authoring notes, unavailable main agent). On the agent path the
activation is prepared in memory and its durable write is deferred until every
refusing preflight passes, so a refused launch leaves the ticket unchanged. A
`ticket.py` path activates just before the script runs, because running user
code is already work starting. `done` and `canceled` are refused untouched.

`blocked` resumes only from an interactive TTY and only when open asks exist;
the prompt gains the resolve-or-re-block preamble (`coga/prompt-composition`).
If the session, script, or any preflight ends with the ask still open,
`_reblock_unresolved_resume` puts the ticket back to `blocked` (restoring the
step a script transition cleared) so blocker queues keep reporting it.
TTY-less launches of a blocked ticket are refused until `coga unblock`.

Divergent workers are visible and recoverable in git; a lock's stale state
is not. Megalaunch's claim and the local state lock are not ownership locks
([launch claims](../internals/launch-claims/SKILL.md)).

## Phases and routing

A directory ticket with the exact sibling `ticket.py` runs it headlessly
first ([script tickets](../script-tickets/SKILL.md)). Only an agent phase
composes a prompt and requires stdin and stdout to both be TTYs.

The operator is derived, never stored per step: `bump.resolve_operator` reads
`owner`, the frozen main-agent choice, and the step's `assignee:` role. An
owner-held step is a hard handoff and launch refuses it. `--agent <type>`
selects a configured agent for this launch only and never rewrites the
ticket. On an owner step it is the human assist
([human assist](../internals/human-assist/SKILL.md)); on an agent step it is
an ordinary override that continues (`consecutive_agent_override`) only while
the first and each directly following step *explicitly* declare
`assignee: agent`. An omitted role, `owner`, or `other-agent` ends it for the
rest of the launch. An override cannot repair invalid routing inputs.
On an override of an agent-held step, a later lifecycle line's
`[agent:<name>]` credits the configured operator, not the override; to
attribute it to the CLI that actually ran, read the preceding
`launched (operator=…, launch_agent=…, agent=…)` line's `launch_agent=`. An
assist on an owner-held step is the exception: its lines credit the assisting
agent ([coga/internals/human-assist](../internals/human-assist/SKILL.md)).

## Agent preflight order

Agent type and CLI lookup (`shutil.which`), a full prompt composition (a
missing layer refuses), declared secrets (`build_launch_env`), push auth
(`git push --dry-run`; skipped for bootstrap targets, `[git].enabled = false`,
or no resolvable remote).
Only then is the deferred activation written and `active` flipped to
`in_progress` (posting `▶️`). Launch never probes `gh` for PR state
(`coga autoclose` handles merged PRs). Git runs non-interactively, so a
credential-less remote fails fast; this entry gate is fatal, while a later
mid-session sync miss is reported and non-fatal.

## The step chain

Each step spawns a fresh agent process through the shared spawn path
([agent spawn](../internals/agent-spawn/SKILL.md)). After a clean exit the
supervisor rereads the ticket and continues only when the task is still
`in_progress`, the step advanced, and the next operator is an agent
(`agent` and `other-agent` rotate CLIs). It stops at owner handoffs,
terminal, paused, or blocked status, a workflow-less ticket, no progress,
an unresolvable operator, a missing CLI, a deleted task directory, a timeout,
or a non-zero exit. A bootstrap target never chains. Sessions not run under a
live `coga launch` do not chain: after `coga bump`, stop and relaunch.
Every exit path of an exempt launch refreshes a control checkout from control
(`git.refresh`); a prepared launch returns its checkout instead.

## Options and exits

- `--prompt-report` prints each composed layer, exact refs, bytes, and
  `characters / 4` token estimates without spawning. It refuses a `ticket.py`
  target and never executes ticket code, but it does refresh the agent-skill
  view. Known defect: `cli._should_sweep_coga_state` counts every `launch`
  as sweeping, so the end-of-command state sweep still runs after a report.
- `--idle-timeout` / `--max-session` (off by default) tear down a stalled or
  runaway REPL; the launch then exits 124 and does not chain.
- Refusals exit 2; a checkout-boundary entry refusal, a stale recurring
  gate, and an unreconciled released megalaunch admission exit 75, which
  skips the end-of-command sweep; a non-zero agent or `ticket.py` exit
  propagates.
