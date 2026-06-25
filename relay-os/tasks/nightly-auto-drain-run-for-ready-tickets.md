---
slug: nightly-auto-drain-run-for-ready-tickets
title: Nightly auto-drain run for ready tickets
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/cli
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
step: 2 (review-design)
---

## Description

Make spare overnight token budget (e.g. an unused Max allotment) useful. Add a
**recurring orchestrator task** — fired by `relay recurring`, modeled on Dream —
that at night scans the backlog of tickets **flagged ready for autonomous
execution**, checks how much Claude and Codex usage is left, and launches as many
ready tickets as the budget allows — **routing each ticket to whichever agent
still has budget**. It parks any blocker without stalling the rest of the night
and leaves a legible per-run record that the morning Slack digest surfaces.

The two things that make this its own ticket (neither is in the drain sibling):

- **It is a recurring *task*, not a Python hook.** A template under
  `relay-os/recurring/auto-drain/`, a `script` step,
  legible like Dream — its own blackboard/log per run, visible in
  `relay recurring list`. Dream is the precedent that a recurring task launching
  other tasks is a blessed pattern, not a recursion to avoid.
- **It reattributes across agents.** The drain sibling respects each ticket's
  existing assignee and merely *skips* an exhausted agent. This task *routes* a
  ready ticket onto whichever of Claude/Codex still has budget, to actually spend
  the leftover allotment instead of leaving Codex idle because the queue happened
  to be Claude-assigned.

**The launch count is emergent, never chosen upfront** — it depends on free
tokens, and each launch spends them. So the orchestration is a greedy adaptive
loop, not a batch (see Proposed Shape). Reattribution and the budget stop are the
same per-step decision: *"which agent, if any, can take the next ready ticket?"*
When neither can, the night is done.

**Ownership is deliberately split** (full detail on the blackboard): the drain
sibling owns the *engine* (usage probes + budget guards + selection, in
`src/relay/drain.py` / `src/relay/usage.py`); this task owns the *trigger,
orchestration loop, and reattribution*. It imports the engine — it does not
re-probe usage or re-derive guards.

## Acceptance Criteria

- [ ] **A recurring template exists** at `relay-os/recurring/auto-drain/`
      (`schedule: "0 2 * * *"`), live copy + packaged mirror under
      `src/relay/resources/templates/relay-os/recurring/…` kept byte-for-byte in
      sync (CLAUDE.md seed-sync rule). It is a `script` step (exempt from the
      `autonomy: auto` recurring freeze), get-or-create + one-live-task semantics
      like every other recurring template.
- [ ] **"Ready for autonomous execution" is defined in one place** an author can
      follow: a ticket is drain-eligible iff `status: active` **and**
      `autonomy: auto` **and** `assignee` resolves to a configured agent type
      **and** its frozen workflow has no human/owner-gated step (an
      `autonomy/fully-automated`-shaped workflow). It must **not** be a recurring
      period task (no `tasks/recurring/` path). The predicate reuses the drain
      sibling's selection helper — no second eligibility function.
- [ ] **The orchestration is an adaptive sequential loop**, not a fixed batch:
      probe Claude+Codex budget → if any agent passes its guard and a ready ticket
      remains, pick the oldest-first ready ticket, route it to a passing agent, and
      launch it → re-probe → repeat. The loop terminates when no agent passes its
      guard **or** no ready ticket remains. No precomputed ticket count anywhere.
- [ ] **Cross-agent reattribution** is implemented and bounded: a ready ticket is
      **routable by default** and launched on whichever configured agent currently
      passes its budget guard; a ticket may **opt out** with an explicit pin marker
      (decided — default routable). The reattribution for a given launch is recorded
      in the run blackboard; the launch routes via a `relay launch <slug> --agent
      <type>` override without rewriting the ticket's `assignee` (preferred — no
      frontmatter scribble), unless the implement step finds a reason to persist it
      through the sanctioned path.
- [ ] **Budget stop is delegated, not reimplemented.** The loop calls the drain
      sibling's `UsageProbe` / `budget_allows_launch`; an unreadable or
      below-guard agent is conservatively treated as "no budget" for that agent
      and never as "safe to launch". This task adds **zero** new usage-reading or
      threshold code.
- [ ] **Blockers park, the night continues.** A ready ticket that hits a blocker
      calls `relay panic` (async-park behavior) and the loop advances to the next
      ready ticket rather than aborting the run. Verified by test (a parking/
      non-zero launch mid-loop does not end the remaining queue). If async-park
      hasn't guaranteed this for this loop, it is filed back to that sibling.
- [ ] **De-dup with the sibling hook (decided).** This task and the sibling's
      `[recurring.drain]` post-sweep hook do not both drain: the sibling exports
      its engine and drops its own auto-trigger; this `auto-drain` task is the sole
      trigger. The scope change is agreed with the sibling (implement step 3) before
      this task's implement begins.
- [ ] **The auto path is gated, loudly.** Implement does not wire/verify the live
      `autonomy: auto` launches until BOTH
      `auto/stream-agent-progress-in-auto-mode-and-recurring-l` has re-enabled
      `autonomy: auto` launches AND
      `drain-pending-auto-tickets-with-leftover-session-b` (the engine) has
      merged. If either is unmet, ship only the gate-free subset (template +
      "ready" definition + reattribution/loop logic unit-tested against a mocked
      engine) and report the blocker — never ship a loop that can only fail at
      launch.
- [ ] **Per-run record + morning summary.** Each run writes a legible record to
      its own blackboard (launched / reattributed / parked / skipped-for-budget),
      and overnight Done tickets surface in the existing 9am `digest/post` via the
      spool. No new morning-report mechanism unless the owner reopens it at review.
- [ ] `python -m pytest` passes and `relay validate --json` is clean (modulo the
      pre-existing unrelated backlog failures). New loop/reattribution logic has
      unit tests with the engine + agent launches mocked (no live network/launches
      in the suite). `example/` fixtures updated if selection needs them.

## Proposed Shape

The engine (probes, guards, selection) is the sibling's `src/relay/drain.py` /
`usage.py`. This task adds the recurring template, the orchestration loop, and
reattribution — thin glue on top of that engine.

1. **Recurring template `relay-os/recurring/auto-drain/ticket.md`** (+ packaged
   mirror). `schedule: "0 2 * * *"`, `autonomy: auto` template with a single
   `script` step (exempt from the recurring freeze; the *launched* tickets are what
   the streaming gate governs). Its body documents the loop and the "ready"
   definition for human legibility, the way Dream's body documents its known-skill
   pass.
2. **Orchestration as a known script skill**, e.g.
   `relay-os/bootstrap/skills/.../auto-drain` with a `script:` entry point, OR a
   thin `relay`-internal callable the script invokes. It:
   - selects ready tickets via the sibling's selection helper (oldest-first),
     **excluding any whose frozen workflow has a human/owner-gated step** (decided:
     don't start structurally-gated work overnight);
   - runs the **adaptive loop**: for each step, probe each configured agent
     (`UsageProbe`), build the set of agents passing `budget_allows_launch`,
     pick the oldest ready ticket, route it to a passing agent (its own if it
     passes, else — if routable — any passing agent), `relay launch` it
     (engine path), then re-probe;
   - stops on no-passing-agent or empty queue; treats a parked/failed launch as
     "park and continue" (does not abort);
   - appends a `## Auto-Drain Run` record to the run blackboard.
3. **Reattribution helper** (the net-new logic; folds in the empty
   `v2/autoroute-agent-based-on-remaining-usage` draft). Input: a routable ready
   ticket + the set of budget-passing agents. Output: the chosen agent. Launch via
   `relay launch <slug> --agent <type>` (no ticket rewrite, preferred). Tickets are
   **routable by default**; one carrying the explicit pin marker is never rerouted
   (decided).
4. **De-dup coordination** with the drain sibling before implement (decided):
   sibling exports the engine and drops its own `[recurring.drain]` auto-trigger;
   this `auto-drain` task is the sole drain trigger.
5. **Tests**: the loop terminates on exhausted budget; reattributes a
   Claude-assigned ready ticket to Codex when only Codex passes; parks-and-continues
   on a panicking launch; never launches a pinned ticket on the other agent; never
   launches a non-ready or `recurring/` ticket. Engine + launches mocked.
6. **Order of work:** template + "ready" definition + loop/reattribution logic +
   unit tests (engine mocked) are buildable now. The live auto-launch verification
   waits on the gate per the Acceptance blocker.

## Out of Scope

- **The usage probes, session/weekly budget guards, oldest-first selection,
  `src/relay/drain.py` + `src/relay/usage.py` engine** — owned by
  `drain-pending-auto-tickets-with-leftover-session-b`. Imported, not reimplemented.
- **Re-enabling `autonomy: auto` launches / streaming agent output** — owned by
  `auto/stream-agent-progress-in-auto-mode-and-recurring-l` (the hard gate).
- **Park-on-blocker mechanism + sweep-doesn't-abort guarantee** — owned by
  `async-park-and-continue-on-block`. This task confirms and consumes it.
- **Autonomy-tier classification at authoring time** — owned by
  `wire-autonomy-triage-into-impl-ready-workflows`.
- **Per-session usage capture + `relay usage`** — shipped by `track-usage-of-llm`.
- **A general daytime autoroute surface** — this task ships reattribution for the
  nightly drain; if a reusable daytime autoroute is wanted later it can lift this
  helper, but generalizing it is not in scope (`v2/autoroute-…` is folded in as
  superseded for the nightly case).
- **A Relay-managed cron daemon / in-process timer** — explicitly never; the user
  schedules `relay recurring` (e.g. via `cron.sh`). Relay does not run on a timer.
- **Dollar-cost accounting** — tokens only, per `track-usage-of-llm`.

## Context

This ticket sits on top of several in-flight tickets; their confirmed state and
the ownership split are recorded on the blackboard (`## Design notes`). The hard
gate is auto-mode streaming — the live auto-launch path must not be wired until
that gate clears and the engine sibling merges (see the gated Acceptance item).
Relay's no-implicit-cron stance (see `relay/cli`, `relay/architecture`) is
intentional: scheduling is "wire `relay recurring` into *your* scheduler" (the
`cron.sh` seam), not "Relay runs on a timer." Dream
(`relay/architecture`, `relay-os/recurring/dream/`) is the structural model for a
recurring orchestrator task that launches child work.

<!-- relay:blackboard -->

## Design notes (step 1: design)

### Direction (owner, 2026-06-24) — revised after first pass
First pass framed this as `cron.sh` wiring + a post-sweep drain hook. **Owner
reframed it: model the nightly drain as a *recurring orchestrator task* (the
Dream pattern) fired by `relay recurring`, that scans ready auto tickets, checks
remaining Claude+Codex usage, and launches what fits — reattributing a ticket to
whichever agent still has budget.** Two things distinguish it from the drain
sibling, neither of which that sibling covers:
1. **Recurring task, not a Python hook.** A real template under
   `relay-os/recurring/`, legible like Dream — its own blackboard/log per run,
   visible in `relay recurring list`. The Dream precedent ("the parent task
   orchestrates child script tasks") settles that a recurring task launching
   other tasks is a blessed pattern, not a weird recursion.
2. **Cross-agent reattribution.** The drain sibling respects each ticket's
   existing assignee and only *skips* an exhausted agent. This task instead
   *routes* a ready ticket onto whichever of Claude/Codex still has budget. Safe
   because "ready" = fully-automated-tier = agent-agnostic by construction. The
   `v2/autoroute-agent-based-on-remaining-usage` draft is empty, so this is
   net-new; owner's call is to own reattribution **here** and fold/close that
   draft as superseded.

**Emergent count (owner, 2026-06-24).** Owner flagged: you can't decide how many
tickets to run upfront — it depends on free tokens, and each launch spends them.
So the orchestration is a **greedy adaptive loop**, not a batch: probe → if any
agent has budget and a ready ticket remains, route+launch the oldest → **re-probe**
(budget just dropped; Claude's probe is free) → repeat until no agent has budget
or the queue is dry. Reattribution and the budget stop are the *same* per-step
decision: "which agent, if any, can take the next ticket?" Both-exhausted ends
the loop. This matches the drain sibling's sequential re-probe loop; this task
adds the routing.

### Ownership split (this task vs the drain sibling)
- **Drain sibling (`drain-pending-auto-tickets…`) = the ENGINE.** `UsageProbe`s
  (Claude OAuth `/api/oauth/usage`, Codex rollout `rate_limits` snapshot),
  session+weekly budget guards (`budget_allows_launch`), oldest-first selection,
  `src/relay/drain.py` + `src/relay/usage.py`. This task *imports and consumes*
  these — it does not reimplement probing or guards.
- **This task = the TRIGGER + ORCHESTRATION + REATTRIBUTION.** The recurring
  template, the adaptive launch loop, the cross-agent routing, the per-run
  legible record, park-continue confirmation, morning-summary wiring.
- **De-dupe coordination (open question #1, raised to important):** we must not
  run *both* the sibling's post-sweep hook *and* this task, or the queue
  double-drains. Cleanest: the sibling's hook becomes engine-only (no
  auto-trigger), this task is the sole trigger. That is a scope change to
  in-flight work — flag for owner/sibling, do not silently override.

### Dependency state (confirmed 2026-06-24)
| Dependency | Status | Owns |
|---|---|---|
| `auto/stream-agent-progress-in-auto-mode-and-recurring-l` | **active, step 1 implement — NOT shipped** | re-enabling `autonomy: auto` launches |
| `drain-pending-auto-tickets-with-leftover-session-b` | **in_progress, step 3 implement** | drain loop, `UsageProbe` (Claude OAuth + Codex rollout snapshot), session+weekly budget guards, oldest-first, stop-on-fail, one-line Slack post, `[recurring.drain]` config, `src/relay/drain.py` + `src/relay/usage.py` |
| `wire-autonomy-triage-into-impl-ready-workflows` | in_progress, step 1 design | autonomy-tier classification at authoring |
| `async-park-and-continue-on-block` | draft, step 1 implement | park-on-blocker + sweep-doesn't-abort |
| `track-usage-of-llm` | **done ✅** | per-session usage records + `relay usage` |

**Hard gate:** auto streaming (`auto/stream-...`) is unshipped → `autonomy: auto`
launches stay disabled → the nightly drain's auto path cannot run end-to-end yet.
This ticket's implement step MUST NOT start until that gate clears AND the drain
sibling merges. Recorded as an explicit blocker in Acceptance Criteria.

### Key facts that shaped the spec
- **`cron.sh` already exists** (`relay-os/scripts/cron.sh` + packaged mirror) and
  already `exec relay recurring` under a pidfile lock. The drain sibling makes
  `relay recurring` auto-drain after the sweep (gated by `[recurring.drain]`,
  off by default). So the "nightly auto-drain entry point" = schedule `cron.sh`
  at night + enable `[recurring.drain]`. No new daemon, no new entry binary.
- **Morning summary already exists.** `relay-os/recurring/digest/ticket.md`
  (`digest/post`, `schedule: "0 9 * * *"`) posts one Slack digest of Done tickets
  + merged commits each morning. Overnight-drained Done tickets spool into it via
  `relay.notification.notify` automatically. So "surface results to Slack in the
  morning" = lean on the existing 9am digest, not a new roll-up. The drain
  sibling's own one-line post is the *live* overnight signal.
- **"Flagged ready for autonomous execution"** resolves to shipped primitives:
  `autonomy: auto` (the execution axis, formerly `mode:`) on an `active` ticket
  assigned to a configured agent type, realized through an all-agent
  (`autonomy/fully-automated`) workflow with no human/owner gate. This matches
  the drain sibling's eligibility filter — confirm parity, don't fork it.

## Decisions (resolved by owner, 2026-06-24)
1. **De-dup with the drain sibling → sibling = engine, this task = sole trigger.**
   `drain-pending-auto-tickets…` drops its own `[recurring.drain]` auto-trigger
   and exports its probes/guards/selection as an importable engine; this
   `auto-drain` recurring task is the single thing that triggers a drain. Requires
   a scope agreement with that sibling (currently implement step 3) — coordinate
   before this task's implement begins.
2. **Human-gated `autonomy: auto` tickets → not selected.** Selection requires the
   frozen workflow have **no** human/owner-gated step (an all-agent
   `autonomy/fully-automated` shape). A ticket that would park on a human step is
   never launched, so overnight budget is never spent reaching a wall it can't
   pass. (Async-park still covers a *mid-run* blocker; this is about not starting
   structurally-gated work.)
3. **Reattribution → routable by default, explicit pin to opt out.** Any ready
   ticket is freely routable across Claude/Codex; a ticket opts out of rerouting
   with an explicit pin marker for model-/agent-specific work. The pin mechanism
   (a frontmatter flag vs. a concrete-assignee convention) is a small
   implementation choice for the implement step — keep it explicit and documented;
   default behavior is routable.
4. **Template name + schedule → `recurring/auto-drain`, daily 2am (`0 2 * * *`).**
   Lives at `relay-os/recurring/auto-drain/` (+ packaged mirror). The name drops
   the time-of-day implication — the user's own cron decides when `relay recurring`
   actually fires; `0 2 * * *` is the template's own schedule gate.

### Still-default (no objection raised — revisit at review if wanted)
- **Morning summary**: lean on the existing 9am `digest/post` + the task's own
  per-run blackboard record; add a dedicated live "overnight run report" post only
  if the owner wants one at review.
- **Sequencing/gate**: build the template + selection + adaptive loop +
  reattribution + unit tests now (engine mocked); hold the *live* auto-launch
  verification until the streaming gate clears and the engine sibling merges.
