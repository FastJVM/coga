---
slug: v2/autotrigger-ticket-type
title: autotrigger ticket type
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills:
- bootstrap/ticket
workflow:
  name: autonomy/assist-only
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-relay
    skills: []
    assignee: agent
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
  (each fire creates a fresh task instance — today's recurring
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
| **recurring**                | the recurring create (re-stock)| recurring   |

`relay-os/recurring/` was always "auto-create"; the `idle-eligible`
proposal was always "auto-launch." Both are the same concept — *who
fires the `active → in_progress` transition* = the system — which is
exactly the unification this ticket exists to name.

### Open questions

Open design questions worth surfacing in the body so a future
session has them on hand:

- File shape for recurring autotriggers — a recurring source can't
  itself be the running task; needs to be template-shaped or have a
  creating rule.
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Session 1 — concept capture

Goal of the ticket (per nick, interactive): define a unified
**autotrigger** ticket type that subsumes both today's recurring
templates and the proposed `idle-eligible` flag. Some autotriggers
recurring, some one-shot. The ticket is **draft only** — no
implementation lands here, just locking the mental model.

### Decisions made this session

- Autotrigger is the umbrella; recurring becomes a flavor of it
  (`cardinality: recurring` + `triggers: [{type: schedule, …}]`).
- Idle/budget-aware execution is also a flavor (`type: idle`).
- Trigger condition and cardinality are orthogonal.
- Multiple triggers on one ticket OR together (default semantics).
- Implies an orchestration layer, but no new daemon required —
  cron handles time triggers, idle triggers run in-session.

### Skill note

`bootstrap/ticket` is referenced in the frontmatter but the SKILL.md
does not exist (`relay-os/skills/bootstrap/` only has `dream/`).
Followed the `_template/ticket.md` structure instead: just
`## Description` and `## Context`, kept tight. Worth opening a
follow-up to actually write the bootstrap/ticket skill so future
draft-fleshing sessions have guidance.

### Open threads for next session

- Frontmatter syntax — the YAML sketch in earlier draft was
  illustrative. Final shape belongs in an implementation ticket.
- Migration plan for `relay-os/recurring/` once autotrigger lands.
- Whether `mode: auto` is implied or independent for autotrigger
  tickets.

## Session 2 — model collapse + draft finalized

Worked the mental model with nick interactively. Landed on a tighter
formulation than session 1:

- **No new status needed.** `active` already means "approved, ready,
  waiting to be launched." `relay launch` owns the `active → in_progress`
  transition (src/relay/commands/mark.py). An autotrigger just makes a
  *trigger* the owner of that same transition instead of a human.
- **Launch and recurring are the same firing act.** Both move a ready
  (active) ticket → in_progress. They differ in ONE thing: whether a
  fresh ready ticket is re-stocked after `done`. one-shot = no re-stock;
  recurring = re-stock.
- **"auto" = system does a human gesture:** launch (one-shot) replaces
  `relay launch`; recurring replaces the recurring create.

Wrote all of this into ticket `## Context` (definition + lifecycle +
re-stock table). Set `workflow: autonomy/assist-only` (design/vocabulary
deliverable — human owns the mental model; Q2 of triage fails).
contexts stay [] — body is self-contained.

Still draft. nick launches after review.

## Evaluator review

Independent cold review (Session 2). Verdict: solid concept ticket,
ready to launch — with one factual correction and two flags.

1. Clarity — yes. Crisp one-sentence definition, states what's unified
   and why-now, explicitly bounds to "concept-capture only." Two-axis
   model + ASCII lifecycle + "gesture it replaces" table do real work.

2. Workflow fit — correct. `autonomy/assist-only` is right: taste/
   judgment work, human owns the result, agent produces support
   material (agent-produces → human-owns-and-finishes). No mismatch.

3. Contexts — none attached; defensible but not free. Body argues from
   first principles. Could attach `principles/` + `architecture/` so the
   "no new status / no new daemon" claims are checkable rather than taken
   on faith. Minor gap.

4. Scope — reasonable and well-disciplined. Explicitly pushes impl,
   frontmatter syntax, migration, event/webhook out of scope. It's the
   umbrella the impl tickets hang under, not a build ticket.

5. Framing assumptions:
   - [FIXED] file citation was wrong: the active→in_progress flip is
     `mark_in_progress` in src/relay/mark.py, fired by relay launch
     (src/relay/commands/launch.py:286), NOT commands/mark.py (which only
     does active/paused/done). Claim itself (launch owns the transition)
     is accurate.
   - "recurring = re-stock after done" is a clean abstraction but glosses
     a flow that misfires today — see live tickets
     detect-recurring-runs-that-mark-done-without-advan,
     recover-recurring-runs-orphaned-when-the-superviso,
     fix-recurring-templates-not-instantiated. Fine for concept-capture; human
     shouldn't think re-stock is a solved trivial step.
   - [FIXED/annotated] the two "related tickets" slugs don't exist as
     task dirs; annotated in body as planned-not-created with pointers to
     the live recurring cluster.

Bottom line: clear, correctly scoped, right workflow. Pre-launch fixes
(a) file citation and (b) dangling slugs are done; (c) attaching
principles/+architecture/ is optional.
