---
slug: review-slack-channels
title: review slack channels
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/important
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

`coga-important` has no automatic producers. The `important=True` route exists
end to end — `[notification.slack].important_webhook` in config,
`SlackChannel.webhook_for` in `src/coga/notification/slack.py:66`, the
`--important` flag on `coga slack` — but the flag is reachable only by a human
typing it, and **nothing in the repo calls it**. Every hit for `--important`
across the tree is documentation or the implementation itself. The result is a
second channel with a webhook, a config path, and a governing context, sitting
empty, while 100% of traffic lands in `coga-flow`.

This ticket gives `coga-important` its first automatic producers by routing
exactly four **failure** events there. It does **not** widen the bar defined in
`coga/important`: each of the four requires a human to repair something, and
none is already attached to a ticket the owner will see — which is precisely
the distinction that context draws when it excludes blockers ("an alert has no
ticket, which is the whole reason it needs a channel"). Blockers, blocker
reminders, done/canceled outcomes, the daily digest, launch starts, and
`bump --message` all stay in `coga-flow`, and every currently silent lifecycle
event stays silent.

The audit behind this ticket also found that `coga/sync`'s live-surface
inventory is no longer exhaustive; correcting it is in scope.

## Context

### The four events to route

| # | Emitter | Current call | Why it qualifies |
|---|---|---|---|
| 1 | Recipe failed (non-zero exit) | `src/coga/recurring_runner.py:809` — `post(...)` | The task is left unfinished and needs diagnosis; no ticket queues it. |
| 2 | Recurring scan errors | `src/coga/recurring_runner.py:2228` — `notify(kind="recurring-error")` | Scheduled work was skipped and templates need repair. |
| 3 | Recurring watchdog timeout | `src/coga/mark.py:704` — `mark_paused` → `notify(kind="recurring-error")` | A wedged run was paused and needs intervention. |
| 4 | Declared period state did not advance | `src/coga/mark.py:321` — `post(...)` inside `_warn_if_state_not_advanced` | The next run silently duplicates work until a human repairs the high-water state. |

Events 2 and 3 are digest-spooled today. **Do not change their cadence.** They
keep spooling; the destination choice applies at delivery, so the installed
digest still aggregates them into one daily post. This means
`notification.notify` needs to carry an important destination through to its
*live fallback* path only (when no digest ticket is installed). A spool record
stays delivery-neutral — `commands/digest.py` owns the aggregate's destination
— so there is never both a live post and a spooled record for one event.

### Decision: fail-loud is preserved everywhere (owner call)

`SlackChannel.webhook_for(important=True)` currently raises rather than falling
back to the flow webhook, and the shipped template leaves `important_webhook`
commented out (`src/coga/resources/templates/coga/coga.toml:87`). **Keep that
behavior unchanged for both automatic and manual routes.**

Accepted cost, stated explicitly so it is not rediscovered as a bug: once these
four routes are automatic, a repo that has not exported
`COGA_IMPORTANT_WEBHOOK_URL` will crash the first time a recipe fails or a
recurring scan errors — and because all four events are themselves failures,
the crash destroys the failure notification that triggered it. The owner
weighed this against a flow fallback and chose fail-loud. Treat configuring the
second webhook as an operational prerequisite, make that prerequisite explicit
in `coga/sync` and the shipped template comment, and add a `coga validate`
warning when `[notification].channels` includes slack and `important_webhook`
is unresolved — a warning at validate time is consistent with a crash at post
time and converts a 3am blackout into a setup-time nudge.

### `coga/sync` inventory is stale

`coga/contexts/coga/sync/SKILL.md` is 50 KB — **read it, do not attach it**; the
facts needed here are copied above. Its live-surface list enumerates `block`,
blocker reminders, `coga slack`, `bump --message`, and `launch`. The audit found
four live posters absent from that list:

- `src/coga/mark.py:321` — stale declared period state (moving to important, #4)
- `src/coga/recurring_runner.py:809` — recipe failure (moving to important, #1)
- `src/coga/dream_validate_drift.py:426` — Dream drift summary (**stays flow**)
- `src/coga/commands/megalaunch.py:147` — megalaunch drain summary (**stays flow**)

Update the inventory so it is exhaustive again, including the two that stay in
flow.

### Prior art — read but do not trust

`coga/tasks/v2/move-some-alerts-to-coga-important-instead-of-coga.md` is paused
at `review-design` with a 19-row source-derived routing matrix. **The owner has
declined its premise** — it widens the bar to "human action or high-signal
outcome" and routes `mark done`, the digest, megalaunch and Dream summaries to
important. This ticket deliberately does not. Its matrix is still useful as a
call-site inventory, but it is stale: it cites `commands/launch_script.py` three
times and that module no longer exists in the tree (only a stale `.pyc`).
Verify every call site against source. That ticket should be canceled once this
one is approved.

### Repo conventions

Per `CLAUDE.md`: behavior changes update the matching context in the same PR,
and the packaged copies under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/` must stay in sync
with the live copies under `coga/contexts/coga/`.

## Acceptance Criteria

- [ ] The four events above deliver to the important webhook; every other
  emitter's destination and cadence is unchanged, and no currently silent
  event becomes a notification.
- [ ] Events 2 and 3 still append exactly one delivery-neutral spool record
  with the current schema when the digest is installed, and reach important
  only through the daily aggregate — never as a duplicate live post.
- [ ] `notification.notify` accepts an important destination and forwards it to
  `post` **only** on the no-digest live-fallback path.
- [ ] `coga slack --important` behavior is unchanged.
- [ ] `webhook_for(important=True)` still fails loud with no fallback, for both
  automatic and manual routes.
- [ ] `coga validate` warns when slack is a selected channel and
  `important_webhook` is unresolved.
- [ ] `coga/contexts/coga/sync/SKILL.md` separates cadence from destination,
  lists all four new important routes, and its live-surface inventory also
  includes the Dream drift summary and megalaunch drain summary that remain in
  flow.
- [ ] `coga/contexts/coga/important/SKILL.md` keeps its existing bar — no
  rewrite of the tune-out or blocker arguments — and gains a short note that
  unattended failure events qualify under the same "no ticket holds it" test.
- [ ] The shipped template comment at
  `src/coga/resources/templates/coga/coga.toml` states that
  `important_webhook` becomes required once recurring jobs run.
- [ ] Packaged context copies match their live counterparts byte-for-byte.
- [ ] Tests assert the destination by **webhook URL**, not just an
  `important=True` keyword, with controls proving flow posts still use the
  primary URL and silent paths make no request. Cover: recipe failure, scan
  error (digest and no-digest), watchdog timeout, period-state warning, plus
  unchanged controls for block, blocker reminders, done, launch start,
  `bump --message`, and message-less bump.
- [ ] The period-state warning still cannot undo a successful `mark done` when
  its important post fails (its existing exception guard is preserved).
- [ ] `python -m pytest` and `coga validate --task review-slack-channels` pass.

## Out of Scope

- Widening the bar to outcomes — `mark done`, `mark canceled`, the daily
  digest, megalaunch drain summaries, and Dream summaries stay in `coga-flow`.
- Routing blockers or blocker reminders to important. The owner explicitly
  agreed with `coga/important`'s existing argument that the ticket is already
  the queue.
- Any change to live-vs-digest cadence.
- A flow fallback for a missing `important_webhook` (decided against above).
- `slack_important_recipient` / mention-envelope work, and reviving the closed
  unmerged PR #578.
- Message text, emoji, GIF selection, digest rendering, or the JSONL spool
  schema.
- New route flags such as `bump --important`, or inferring importance from
  message contents.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
