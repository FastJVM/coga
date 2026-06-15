---
title: autotrigger ticket type
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills:
- bootstrap/ticket
workflow: autonomy/assist-only
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

### The model to lock

One-sentence definition:

> An autotrigger is a ticket the system may fire on its own — moving it
> from `active` (ready) to `in_progress` **without a human `relay launch`
> gesture** — when a trigger condition matches.

Two orthogonal axes the model needs to express:

- **Trigger condition** — `schedule` (cron), `idle` (spare budget),
  later `event` / `webhook` / `queue-depth`. Multiple triggers OR
  together by default.
- **Cardinality** — `one-shot` (fires once → `done`) or `recurring`
  (each fire scaffolds a fresh task instance — today's recurring
  template flow).

**Key insight — "fire" is always the same transition.** The status
lifecycle already has the state we need; no new status is required.
`relay launch` already owns the `active → in_progress` start transition
(the flip is `mark_in_progress` in `src/relay/mark.py`, fired by
`relay launch` — `src/relay/commands/launch.py`). An autotrigger simply
makes a *trigger* the owner of that same transition instead of a human:

- `draft` — not approved
- `active` — approved, **ready/armed, waiting to be fired**
- `in_progress` — running now
- `done` / `paused`

So one-shot and recurring are **the same firing act**, and differ in
only one thing — whether anything is re-stocked afterward:

```
every autotrigger:  ready (active)  →  in_progress     (the fire; was: human relay launch)

one-shot:           ...→ done.  end.
recurring:          ...→ done, then re-stock a fresh "ready" (active) ticket for next cycle
```

That is the whole distinction: **one-shot = no re-stock; recurring =
re-stock after done.** The fire itself is identical.

Which means "auto" is just the system performing a gesture a human used
to perform:

| autotrigger does the job of… | human gesture it replaces        | cardinality |
| ---------------------------- | -------------------------------- | ----------- |
| **launch**                   | `relay launch` (fire, in place)  | one-shot    |
| **recurring**                | the recurring scaffold (re-stock)| recurring   |

`relay-os/recurring/` was always "auto-scaffold"; the `idle-eligible`
proposal was always "auto-launch." Both are the same concept — *who
fires the `active → in_progress` transition* = the system — which is
exactly the unification this ticket exists to name.

### Open questions

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
get written. **Note (verified 2026-06-12):** the two names below are
*planned, not-yet-created* slugs — they do not exist as task dirs. Use
them as intended titles, and see the existing clusters for live work:

- `token-budget-aware-idle-execution-of-low-priority` *(not created)* —
  would provide the `idle` trigger. Closest existing: none yet
  (`enforce-a-prompt-token-budget-in-compose` is adjacent but not this).
- `reconcile-recurring-command-spec-contradiction` *(not created)* — the
  recurring side this concept absorbs. Live recurring-hazard cluster to
  read instead: `detect-recurring-runs-that-mark-done-without-advan`,
  `recover-recurring-runs-orphaned-when-the-superviso`,
  `fix-recurring-templates-not-instantiated`,
  `enforce-mode-auto-for-recurring-templates`.

Out of scope here: trigger evaluator implementation, frontmatter
syntax, migration of existing recurring templates, event/webhook
trigger design.
