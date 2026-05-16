---
title: autotrigger ticket type
status: draft
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts: []
skills:
- bootstrap/ticket
workflow: null
---

## Description

Define a unified **autotrigger** ticket type: a ticket the system is
authorized to launch on its own, with no human `relay launch`
gesture. The ticket carries the work *and* the trigger condition
that fires it.

This unifies two ideas already drafted as separate tickets:

- `relay-os/recurring/` templates — fire on cron schedule.
- The `idle-eligible` proposal in `token-budget-aware-idle-execution-of-low-priority` —
  fire when a session has spare token budget.

Same concept, two angles. Naming and modeling it as one type now
prevents two parallel mechanisms from landing and having to be
merged later. Implies an orchestration layer (something evaluates
triggers and fires matching tickets) — but no new daemon: cron stays
the heartbeat for time triggers, idle triggers run inside an
existing session.

This ticket is **concept-capture only**. No code, no frontmatter
finalization, no migration. Goal is to lock the mental model so
downstream tickets (idle execution, recurring consolidation,
orchestration runner) share vocabulary.

## Context

Two orthogonal axes the model needs to express:

- **Trigger condition** — `schedule` (cron), `idle` (spare budget),
  later `event` / `webhook` / `queue-depth`. Multiple triggers OR
  together by default.
- **Cardinality** — `one-shot` (fires once → `done`) or `recurring`
  (each fire scaffolds a fresh task instance — today's recurring
  template flow).

Open design questions worth surfacing in the body so a future
session has them on hand:

- File shape for recurring autotriggers — a recurring source can't
  itself be the running task; needs to be template-shaped or have a
  scaffolding rule.
- Is `triggers:` presence the standing consent that bypasses
  human-launch approval, or do we want an explicit `autotrigger:
  true` flag for legibility?
- Where the idle evaluator runs — has to be in-session (only place
  with budget visibility); likely an end-of-task hook calling
  `relay` to ask what's eligible.
- Audit / Slack legibility — every autotrigger firing should name
  its source ("fired by: schedule" / "fired by: idle"), matching
  today's `relay launch` post.

Related tickets to cross-reference when the implementation tickets
get written:

- `token-budget-aware-idle-execution-of-low-priority` — provides
  the `idle` trigger.
- `reconcile-recurring-command-spec-contradiction` — the recurring
  side that this concept absorbs.

Out of scope here: trigger evaluator implementation, frontmatter
syntax, migration of existing recurring templates, event/webhook
trigger design.
