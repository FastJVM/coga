---
name: coga/state-publication/launch-boundaries
description: Startup, handoff, and usage publication deadlines, the ordinary managed step's commit bound, and explicit accounting for launch paths with separate boundaries.
---

# Launch publication boundaries

Part of [state publication](../SKILL.md). These boundaries reduce bookkeeping
commits without delaying state another operator needs. They do not batch
across commands, agent steps, or processes, or rewrite shared history.

## Ordinary managed agent steps

One successful ordinary managed step makes **three commits**:

1. **Startup:** the final ticket (activation/start and any new branch linkage)
   and the launch audit publish together before a checkout switch or agent
   execution. Activation and start remain distinct audit events, in that order.
   A resumed step with existing linkage still publishes its log-only start
   audit immediately; the line never waits for bump.
2. **Handoff:** bump, mark, or block publishes its finalized ticket and event
   log before returning or releasing the session. The agent's blackboard
   handoff is in this commit. The launcher never waits for usage to publish it.
3. **Usage:** after the agent's final command, session teardown appends and
   publishes usage through the event-aware log-only publisher. Failed or skipped
   publication reports retained lines and preserves the child's result. With
   no new usage line this boundary can add zero commits, but still attempts
   publication or reports failure.

The exact-three workload starts clean and current, with working Git, no
competing publisher, no `ticket.py`, no resumed blocker or recorded assist,
and an agent-held step. The entry can be `draft`, `paused`, `active`, or
`in_progress`; checkout policy stays on control or creates/reuses a branch.
The agent edits only its own handoff and runs one CLI bump to an owner-held
step, writes nothing afterward, and teardown appends one usage record.
Workflow-name activation freezes and selects the main agent within startup.

Count every new commit reachable from remote control from immediately before
CLI launch entry until usage capture, checkout return, and the outer CLI
sweep have finished. Seed commits and existing linkage precede that interval.
Local control must finish at the remote tip. Entry settlement, return, and
the final sweep remain independent publishers and add zero in this workload;
repeating an unchanged sweep adds zero too.

Pre-existing eligible dirt adds its entry publication before the authoritative
read. Another mutating command can publish a handoff edit before bump, and
later eligible edits can add return/sweep publications. Count those events
separately; the ordinary bound does not cover arbitrary agent work and never
authorizes suppressing a sweep or absorbing unrelated dirty roots into a
task's startup transaction.

## Subjects and activity

A startup that starts work uses `Ticket: <slug> — in_progress`, including
activation. Otherwise new linkage uses `Ticket: <slug> — branch <branch>`;
an audit-only resume uses `Log: <slug>`. Lifecycle handoffs keep their existing
subjects, including bump's numbered destination, such as
`Ticket: <slug> — step 2 (review)`.

Ordinary lifecycle subjects count as activity. Ordinary `Log:` and
`Sync coga state` subjects are machine activity; `Log: bootstrap/...` counts
as activity. Recurring/autofix lifecycle events and blocker reminders remain
machine activity. Grouping changes no inactivity classification.

## Paths with separate deadlines

These paths retain their own publication contracts; none opts into ordinary
startup grouping. Counts below assume otherwise clean work and one usage
record for each agent session.

| Path | Boundaries and accounting |
| --- | --- |
| Megalaunch, active or unclaimed `in_progress`, one bump on control | Four: pending claim, admitted generation plus launch audit, bump, usage. Claim and admission straddle held-child release. |
| Explicit megalaunch draft/paused activation | Five in the equivalent case: strict activation adds one before the claim. Retain its rollback/uncertainty semantics. Dependency-drain blocker resolution is durable before claiming. |
| Queue branch creation or other mutating commands | Add their actual publications; the queue does not use ordinary branch preparation. |
| Agent bootstrap, including chat/orientation | Start audit plus usage: two for a no-write session. Agent state writes add their settlements/sweeps; no task lifecycle can substitute for the start audit. |
| Guided authoring (`coga ticket`) | Immediate start audit, usage, guarded authored-set publication: three when the set changes, plus independent agent commands. A refused authored set withholds the sweep. |
| Stateful `ticket.py` | Activation if needed, start if needed, script launch audit before user code, script lifecycle commands, and exit-line settlement/sweep. A clean active script that bumps once makes four; draft adds one, resumed `in_progress` removes one. A later agent phase has its own audit and usage. |
| Stateless script | No task startup audit/lifecycle; count actual writes. |
| Recurring period and delegated bootstrap | Count creation/adoption, strict start/lease checks, delegated audit, child audit/usage, result, and serviced-period ledger publications in their existing order. Neither ordinary nor queue bounds cover the whole run. |
| Exempt/unmanaged launch, recorded assist, blocked resume | Existing routes and diagnostics, with no ordinary bound. |
| Git disabled | No commits and no claim of remote durability. |

Keeping queue activation separate is a scope decision, not a claim that an
atomic activation-plus-claim design is impossible. A resumed ordinary reuse
already used three commits and a resumed queue step already used four; this
change promises no reduction for either case.

Preparation failures, retained startup evidence, and retry procedure are owned
by [the checkout boundary](../../checkouts/launch-boundary/SKILL.md).
Catchable session exits retain publish-or-report cleanup. Uncatchable process
death cannot execute `finally`: the next entry settles retained state.
