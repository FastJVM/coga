---
slug: review-slack-channels
title: review slack channels
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/important
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

`coga-important` has no automatic producers. The `important=True` route exists
end to end — `[notification.slack].important_webhook` in config,
`SlackChannel.webhook_for` in `src/coga/notification/slack.py:66`, the
`--important` flag on `coga slack` — but the flag is reachable only by a human
typing it, and **no shipped code, recipe, recurring template, or alias calls
it**. The only caller anywhere in the tree is `tests/test_commands.py:863`;
every other hit is documentation or the implementation itself. The result is a
second channel with a webhook, a config path, and a governing context, sitting
empty, while 100% of traffic lands in `coga-flow`.

This ticket gives `coga-important` its first automatic producers by routing
four **failure** events there. It does **not** widen the bar defined in
`coga/important`: each of the four is an unattended machine failure whose only
ticket is a *generated* recurring period task that nobody owns as a queue —
unlike a hand-owned blocked ticket, which `coga/important` correctly excludes
because "the ticket itself is already the queue." A generated period task is
nobody's queue; if its failure is not broadcast, nobody looks. Blockers,
blocker reminders, done/canceled outcomes, the daily digest, launch starts, and
`bump --message` all stay in `coga-flow`, and every currently silent lifecycle
event stays silent.

The audit behind this ticket also found that `coga/sync`'s live-surface
inventory is no longer exhaustive; correcting it is in scope.

## Context

### The four events to route

| # | Emitter | Current call | Why it qualifies |
|---|---|---|---|
| 1 | Recipe failed (non-zero exit) | `src/coga/recurring_runner.py:809` — `post(...)` | The task is left unfinished and needs diagnosis; its generated period ticket is nobody's queue. |
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

**Consequence, stated so it is not mistaken for a bug:** this repo has the
digest installed (`coga/recurring/digest/spool.md` exists) and the digest stays
in flow per Out of Scope. So in *this* repo events 2 and 3 never reach
`coga-important` — their important route is reachable only on the no-digest
fallback path, which this repo does not take. The honest local count is **two**
new important producers (events 1 and 4); events 2 and 3 are correctness work
for repos without a digest. Both still need the digest/no-digest test pair.

**Hazard for event 3:** `mark_paused` has three callers and only one of them
notifies. `src/coga/commands/mark.py:125` (manual `coga mark paused`) and
`src/coga/recurring_runner.py:1998` (non-timeout unfinished pause) pass no
`slack_text` and are silent; only `src/coga/recurring_runner.py:1974` (the
timeout path) passes it. Hardcoding the important destination at `mark.py:704`
inside the existing `if slack_text is not None:` guard is safe. Threading a
routing parameter through `mark_paused` instead risks giving the two silent
callers a notification — which would violate the "no currently silent event
becomes a notification" criterion. Prefer the hardcoded form.

### Decision: no flow fallback — `webhook_for` is unchanged (owner call)

`SlackChannel.webhook_for(important=True)` currently raises rather than falling
back to the flow webhook, and the shipped template leaves `important_webhook`
commented out (`src/coga/resources/templates/coga/coga.toml:87`). **Keep that
behavior unchanged for both automatic and manual routes.** Note this is a
decision about `webhook_for`, not a guarantee that every route crashes — event
4 swallows the raise, as detailed below.

Accepted cost, stated explicitly so it is not rediscovered as a bug: once these
routes are automatic, a repo that has not exported
`COGA_IMPORTANT_WEBHOOK_URL` will crash the first time a recipe fails — and
because all four events are themselves failures, the crash destroys the failure
notification that triggered it. This repo is not exposed:
`coga/coga.toml:69` sets `important_webhook` and the variable is exported, so
the risk is a downstream-repo concern.

**Blast radius (larger than a lost notification).**
`src/coga/recurring_runner.py:699-701` calls `_run_recipe_task` with no
`try/except` — it only inspects the returned code. A `typer.Exit(1)` raised
from the important post at line 809 propagates out of the *scan loop*, so a
misconfigured repo skips every remaining due task and the end-of-run
`_broadcast_scan` summary. One unconfigured webhook silently halts the whole
recurring run.

**The owner was shown this blast radius and confirmed fail-loud anyway, with no
call-site guard.** Do not wrap `recurring_runner.py:809` to contain it and do
not reopen the decision — the `coga validate` warning is the chosen mitigation,
which is why that criterion is not optional.

**Event 4 is fail-quiet, not fail-loud.** `webhook_for` raises `typer.Exit`,
whose MRO is `(click.exceptions.Exit, RuntimeError, Exception, BaseException,
object)`, and the guard at `src/coga/mark.py:331` is a bare `except Exception`.
So a missing `important_webhook` on the period-state warning is swallowed and
degraded to a stderr line. Preserve that guard as-is (see the criterion about
not undoing a successful `mark done`) and accept that event 4 does not fail
loud. Do **not** narrow the guard as part of this ticket.

Treat configuring the second webhook as an operational prerequisite, make that
prerequisite explicit in `coga/sync` and the shipped template comment, and add
a `coga validate` warning when `[notification].channels` includes slack and
`important_webhook` is unresolved — a warning at validate time is consistent
with a crash at post time and converts a 3am blackout into a setup-time nudge.
`src/coga/notification/__init__.py:52` already exposes
`preflight_post(cfg, *, important=False)` (used by `commands/block.py:74` and
`commands/launch.py:600`); consider it alongside the validate warning.

### `coga/sync` inventory is stale

`coga/contexts/coga/sync/SKILL.md` is 50 KB — **read it, do not attach it**; the
facts needed here are copied above. The two anchors you need are its live
surface at `:35-48` and its "Live callers (`post`)" list at `:280-289`; both
enumerate the same five — `block`, blocker reminders, `coga slack`,
`bump --message`, `launch`. The audit found four live posters absent from both:

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
call-site inventory, but it is stale in at least two places:

- It cites `commands/launch_script.py` **four** times (lines 125, 128, 134,
  135) and that module no longer exists in the tree (only a stale `.pyc`).
- Its last row attributes the Dream drift summary to packaged
  `bootstrap/dream/tasks/validate-drift/run.py::post_slack_summary`; the live
  emitter is `src/coga/dream_validate_drift.py:426`.

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
- [ ] `webhook_for(important=True)` is unchanged — no fallback added, for
  either automatic or manual routes. Event 4 is the known exception: its
  existing bare `except Exception` at `src/coga/mark.py:331` swallows the
  resulting `typer.Exit`, and that guard is preserved rather than narrowed.
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
- [ ] Packaged context copies match their live counterparts byte-for-byte,
  verified with `diff -q coga/contexts/coga/<name>/SKILL.md
  src/coga/resources/templates/coga/bootstrap/contexts/coga/<name>/SKILL.md`
  for both `important` and `sync`. They match today, so this starts clean.
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

## Dev
pr: https://github.com/FastJVM/coga/pull/696
branch: route-important-failures
worktree: /tmp/coga-route-important-failures

## Implementation notes

- Preserve each event's current cadence; `notify(important=True)` affects only
  the no-digest live fallback, and spool records remain delivery-neutral.
- Keep `SlackChannel.webhook_for` and the period-state warning's broad
  exception guard unchanged. The validation warning is the mitigation for an
  unresolved important webhook.
- The broader v2 routing proposal is already canceled; this branch follows the
  narrower four-failure-event decision in this ticket.
- Added URL-observable regressions for all four failure routes, digest and
  no-digest behavior for both `recurring-error` producers, flow controls, and
  the period-state best-effort guard. The pre-fix focused run failed on each
  new route as expected.
- Implementation now forwards `notify(important=True)` only through its live
  fallback, routes the two direct posters to important, and adds a static
  validate warning for selected Slack with no resolved important webhook.
- A focused eight-file run reached 539 passing tests with three fixture-only
  validation failures caused by the suite-wide deprecated Slack env fallback;
  the baseline validator fixture now explicitly models no notification opt-in,
  and its 82-test suite passes.

## Implemented

- Routed non-zero recurring recipes and stale declared-period-state warnings
  directly to the important webhook.
- Added `important` to `notification.notify`; recurring scan errors and
  watchdog timeouts pass it only to the no-digest live fallback. Installed
  digests still receive one unchanged, delivery-neutral record.
- Added the default, non-network `coga validate` warning for selected Slack
  without a resolved important webhook. `SlackChannel.webhook_for` remains
  unchanged and no call-site containment was added.
- Updated `coga/important`, `coga/sync`, their byte-identical packaged copies,
  the shipped config comment, and `docs/operations.md`. Dream, megalaunch,
  digest, blockers, reminders, starts, done outcomes, and explicit flow FYIs
  retain their prior destinations.

## Verification

- `python -m pytest` — 1752 passed, 1 skipped.
- `PYTHONPATH=/tmp/coga-route-important-failures/src python -m coga.cli validate
  --task review-slack-channels` — all good (1 task).
- From `example/coga`, `PYTHONPATH=/tmp/coga-route-important-failures/src
  python -m coga.cli validate --json` — 2 tasks checked, no issues.
- Both required live/packaged context pairs pass `diff -q`; `git diff --check`
  passes.
- Final diff review clarified the operations guide's best-effort exception for
  post-commit lifecycle notifications and the period-state advisory; routing
  behavior was unchanged.
- Commit: `866be522227d678320e3e91b7b64a1071ff8efd6` (`Route recurring
  failures to important Slack`). The feature checkout is clean.
- Freshness: fetched `origin/main`; `FETCH_HEAD` remained
  `5740ccfd7311bcb6fe632ba5e9be5994bce4036f`, exactly the feature commit's
  parent. `git rebase FETCH_HEAD` reported the branch up to date, and the
  ancestry check passed.

## Peer review

- Started from clean feature commit `866be522` against `main`; reviewing only
  must-fix correctness issues before the mandatory fresh rebase and full suite.
- `codex review --base main` found one P2: the prerequisite warning ignored
  `[notification.slack].enabled = false`, creating permanent false drift for
  the supported solo/dev/CI opt-out. Applying the narrow enabled-state gate,
  regression test, and matching documentation qualification.
- Applied the P2 fix. Focused validation is `83 passed`; the post-fix full
  suite is `1753 passed, 1 skipped`. Live/packaged contexts remain identical
  and `git diff --check` passes.
- Committed the review fix, fetched `origin/main`, and rebased both feature
  commits cleanly onto `9a160d9e`. Final commits are `1a527549` (implementation)
  and `03b8f94a` (peer-review fix); the feature checkout is clean and two commits
  ahead of the fresh base.
- Post-rebase `python -m pytest` is `1753 passed, 1 skipped`; task-scoped
  validation reports `All good (1 tasks checked)`.

## PR

### Summary

- Route four unattended recurring failure signals to `coga-important` while
  preserving every event's existing live-versus-digest cadence and keeping the
  daily aggregate, lifecycle traffic, Dream, and megalaunch in `coga-flow`.
- Warn during validation when enabled Slack has no resolved important webhook,
  while honoring the supported disabled-Slack opt-out and retaining the chosen
  fail-loud delivery policy.
- Update the live and packaged notification contracts, operator documentation,
  shipped config guidance, and URL-observable regression coverage.

### Test plan

`python -m pytest` (1753 passed, 1 skipped); `PYTHONPATH=/tmp/coga-route-important-failures/src python -m coga.cli validate --task review-slack-channels` (all good).
