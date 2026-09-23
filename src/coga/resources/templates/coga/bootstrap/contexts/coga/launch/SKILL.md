---
name: coga/launch
description: What `coga launch <target>` accepts, how status and routing decide what runs, the preflight order before any lifecycle write, the step-chaining supervisor's stop rules, and the `--agent`, `--prompt-report`, and liveness options.
---

# Coga launch

`coga launch <target> [args...]` starts or resumes work on one target. It is
the attended path: a human typed it. Queue draining is `coga megalaunch`
([megalaunch](../megalaunch/SKILL.md)); scheduled work is `coga recurring`.

## Targets

- A task by any unique prefix of its ref. A nested task is its path under
  `tasks/` (`marketing/coga-crm`), exactly as `coga status` prints it.
- `bootstrap/<name>` — a stateless target: no lifecycle, no chaining,
  concurrent launches safe. Its launch log line publishes immediately.
  `coga chat` is the default alias for `launch bootstrap/orient`.
- A `recurring/<name>` period is gated first (control branch, owner,
  verified control catch-up, exit 75 when stale) and a frozen `delegate:`
  period routes straight to its bootstrap target; see
  `coga/recurring/delegation` and `coga/internals/recurring-admission`.

Trailing positional arguments reach an agent prompt as an ordered JSON
`## Launch arguments` block; `ticket.py` receives no operands.

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

## Agent preflight order

Agent type and CLI lookup (`shutil.which`), a full prompt composition (a
missing layer refuses), declared secrets (`build_launch_env`), push auth
(`git push --dry-run`; skipped for bootstrap targets, `[git].enabled = false`,
or no resolvable remote), then a warn-only installed-versus-source skew check.
Only then is the deferred activation written and `active` flipped to
`in_progress` (posting `▶️`). Launch never probes `gh` for PR state
(`coga autoclose` handles merged PRs). Git runs non-interactively, so a
credential-less remote fails fast; this entry gate is fatal, while a later
mid-session sync miss is reported and non-fatal.

The skew check (`version_skew.warn_if_installed_predates_source`, also run by
`coga validate`) compares the installed package's mtime with the last commit
touching `src/coga/` in a Coga source checkout. It never blocks; it skips
non-Coga repos, missing git metadata, bad timestamps, and editable installs,
and cannot see uncommitted `src/coga` edits (it uses commit time).

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
Every exit path refreshes a control checkout from control (`git.refresh`).

## Options and exits

- `--prompt-report` prints each composed layer, exact refs, bytes, and
  `characters / 4` token estimates without spawning. It refuses a `ticket.py`
  target and never executes ticket code, but it does refresh the agent-skill
  view. Known defect: `cli._should_sweep_coga_state` counts every `launch`
  as sweeping, so the end-of-command state sweep still runs after a report.
- `--idle-timeout` / `--max-session` (off by default) tear down a stalled or
  runaway REPL; the launch then exits 124 and does not chain.
- Refusals exit 2; a non-zero agent or `ticket.py` exit propagates.
