---
slug: move-some-alerts-to-coga-important-instead-of-coga
title: move some alerts to coga important instead of coga flow
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/important
  - coga/sync
skills: []
workflow: code/design-then-implement
secrets: null
script: null
---

## Description

Today essentially nothing routes to the coga-important Slack channel: the
`important=` routing flag exists end-to-end but `coga slack --important` is its
only caller. Every other alert — blockers, script failures, recurring scan
errors, watchdog timeouts, the daily digest, step transitions — lands in the
ordinary flow channel, where the ones that need a human get lost in the churn.

Comb through every alert Coga emits and propose a per-alert routing decision,
with a one-line reason each, into `## Proposed Shape`. Park unresolved decisions
under `## Open Questions` on the blackboard. The owner approves or rejects at the
`review-design` gate before any code is written.

Routing is **not** binary per emitter — several are conditional (a script step
advance is routine, a script step *failure* is not). Allow a predicate in the
table rather than forcing every row to important-or-flow.

**The bar is being deliberately widened by this ticket.** `coga/important`
currently says the bar is strictly "a human must act", and explicitly excludes
blockers and things that are merely worth knowing. The owner has decided that is
now wrong: the bar becomes **human action OR high-signal outcome** — blockers,
the daily digest, and work summaries belong in important. Rewriting
`coga/contexts/coga/important/SKILL.md` to state the new bar is part of this
ticket's PR, not a follow-up. Keep the packaged copy under
`src/coga/resources/templates/coga/` in sync.

Rewrite it as a *rebuttal*, not a deletion. The old context makes two arguments
the new one must answer rather than drop, or the next person has no principle to
apply to alert #20:

- **The tune-out argument.** A channel that collects things worth knowing becomes
  a feed people ignore, and then the alert that did need a human is missed inside
  it. State what now holds the middle instead.
- **The blocker argument.** The old bar excluded blockers not because they aren't
  urgent but because a blocker already has a ticket, and the ticket is already a
  queue; the channel exists for things with *no* queue. Routing blockers there
  adds a second queue. Say what coga-important now *is*, if not "things with no
  other home."

## Acceptance Criteria

- A per-alert routing table covering every emitter in the inventory below, each
  with a one-line reason, written into `## Proposed Shape` and approved by the
  owner.
- Approved emitters route to important; the flow-channel ones are untouched.
- `coga/contexts/coga/important/SKILL.md` restated to the widened bar, rebutting
  (not deleting) the two arguments above.
- `coga/contexts/coga/sync/SKILL.md` updated where the widened bar makes its
  live/digest tier prose or its `important_webhook` description stale — CLAUDE.md
  requires the matching context to change in the same PR, and that applies to
  both contexts, not just `coga/important`.
- Packaged copies under `src/coga/resources/templates/coga/` in sync.
- Tests cover routing for each changed emitter.

## Context

### The routing mechanism exists, but it does not reach most emitters

Do **not** assume this is flag-flipping — it is an API change. Verified:

- `notification.post(..., important: bool = False)` —
  `src/coga/notification/__init__.py:45`. Only three inventory rows call `post`
  directly: `commands/slack.py`, `commands/megalaunch.py:133`,
  `commands/digest.py:139`.
- **Every other row goes through `mark.py`** — `mark_done` (`mark.py:80`),
  `mark_in_progress` (`mark.py:349`), `mark_blocked` (`mark.py:372`),
  `advance_step`. They build a `slack_text` and call `post` internally, and
  **none of them accept an `important` parameter.** Threading routing to those
  rows means changing these finalizers' signatures and their call sites.
- **`notification.notify` (`__init__.py:188`) has no `important` parameter at
  all.** Four rows are on the `notify` path (`mark done`, autoclose, script
  completion, both recurring-error kinds) — and the owner named the daily digest
  and work summaries as headline candidates. This is a missing API surface, not a
  per-alert nuance. **The design step must resolve it before those rows are
  implementable**; a digest-spooled event is not live, so "move it to important"
  may mean changing its delivery path, not just its webhook.
- Config keys: `slack_important_webhook` (`config.py:89`),
  `slack_important_recipient` (`config.py:95`).

### Prerequisite decision: fallback vs. crash

`SlackChannel.webhook_for` (`src/coga/notification/slack.py:52`) treats
`important=True` with no `important_webhook` configured as a hard
`typer.Exit(1)` — never a fallback to the flow webhook. `coga/sync` argues this
is deliberate: delivering a human-action alert to the wrong channel while
reporting success is worse than crashing, and the crash is what gets the config
fixed. That argument must be rebutted or preserved explicitly — do not quietly
soften it.

It matters because the shipped template
(`src/coga/resources/templates/coga/coga.toml`) leaves the important webhook
commented out, so routing a *common* event to important crashes every downstream
repo that hasn't configured one. Its blast radius is wider than this ticket's.
Raise it in `## Open Questions`; if it grows past a small guard, it is its own
ticket and this one depends on it.

This repo has `important_webhook` configured
(`env:COGA_IMPORTANT_WEBHOOK_URL` in `coga/coga.toml`), so the change is
verifiable end-to-end here.

### Adjacent gap — decide up front, default to separate

`slack_important_recipient` is resolved and unit-tested but **read by no
emitter** — the `@`-mention triage owner the `coga/important` context promises
does not exist. "Make important triageable" is a different change from "decide
what goes there", so the default is a separate ticket. Flag it in
`## Open Questions` rather than absorbing it silently; this ticket is already at
the upper edge of one ticket's scope.

### Alert inventory (survey done at ticket-authoring time — verify before relying on it)

Two delivery paths: `post()` is live; `notify()` spools to the daily digest and
accepts only kinds `{done, recurring-error}` (`notification/__init__.py:79`).

**Read this table with care.** The "Path" column is the eventual *destination*,
not the code you edit — most rows reach it via a `mark.py` finalizer (see above).
Line numbers have drifted and several are approximate: `bump.py:108` is a
no-workflow bail (`bump.py` contains no `post(` call at all), the "period state
not advanced" post is at `mark.py:185` inside `_notify_stale_period_state`, and
"launch: active → in_progress" and "`mark done`" are the *same* emitter family
rather than independent rows. Re-derive the inventory from source in the design
step; treat this as a navigation aid.

| Event | Emitter | Path |
|---|---|---|
| `coga slack --message` | `commands/slack.py:53` | post (only current `important=` user) |
| `bump --message` step advance | `bump.py:108` | post |
| script step advance | `commands/launch_script.py:424` | post |
| `mark done` | `mark.py:118` | notify `done` |
| auto-close on PR merge | `autoclose.py:197` | notify `done` |
| script ticket completed | `commands/launch_script.py:446` | notify `done` |
| `coga block` | `mark.py:391` | post |
| still-blocked after launch exits | `commands/launch.py:642` | post |
| still-blocked after megalaunch pick | `megalaunch.py:881` | post |
| blocker reminder sweep | `blocker_reminders.py:134` | post |
| launch: active → in_progress | `commands/launch.py:358` | post |
| script launch start | `commands/launch_script.py:162` | post |
| script step failure | `commands/launch_script.py:201` | post |
| megalaunch drain summary | `commands/megalaunch.py:133` | post |
| daily digest | `commands/digest.py:139` | post |
| recurring scan errors | `recurring_runner.py:1693` | notify `recurring-error` |
| recurring watchdog timeout | `recurring_runner.py:1443` | notify `recurring-error` |
| period state not advanced | `mark.py:352` | post (exceptions swallowed) |
| dream validate-drift summary | `bootstrap/dream/tasks/validate-drift/run.py:426` | post |

Deliberately silent today, and should stay silent unless argued otherwise:
`coga create`, `coga unblock`, draft/active/retire transitions, recurring
template creation.

### Out of scope

- Adding new alerts. This is a routing change over the existing set.
- Changing message text, GIFs, or the digest rendering.
- Reworking the live-vs-digest tier design beyond what a specific routing
  decision forces.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
