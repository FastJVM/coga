---
slug: move-some-alerts-to-coga-important-instead-of-coga
title: move some alerts to coga important instead of coga flow
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/important
- coga/sync
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (review-design)
---

## Description

Coga has two independent notification decisions that the current implementation
mostly conflates:

1. **Cadence:** post an event live, batch it through `notification.notify` into
   the daily digest, or keep it silent.
2. **Slack destination:** send a delivered message to the ordinary flow webhook
   or the important webhook.

The second decision is wired end-to-end only for `coga slack --important`.
Consequently blockers, script failures, recurring failures, and Coga's
high-signal work summaries are delivered beside routine starts and FYIs, where
the messages most worth reading are easy to miss.

This ticket widens `coga-important` from a strict human-action queue to the
small, high-signal attention surface humans should read completely. It admits
two classes: an unresolved event that needs human action, and a condensed
outcome that closes or summarizes meaningful work. Routine starts, ordinary
step movement, and unflagged FYIs remain in coga-flow; silent lifecycle events
remain silent. The live-versus-digest cadence does not change: a spooled event
reaches important through the one daily digest, not through a duplicate live
post.

## Acceptance Criteria

- [ ] Every row in the source-derived routing matrix below has the specified
  destination, predicate, and cadence; no existing silent event becomes a new
  notification.
- [ ] `notification.notify` can preserve the important destination when it
  falls back to a live post, while installed-digest events remain one
  destination-neutral spool record and are not posted twice.
- [ ] Blockers, blocker reminders, script failures, stale recurring state, the
  non-empty daily digest, and non-empty work summaries route to the important
  webhook.
- [ ] Done outcomes and recurring errors are delivered through the important
  destination: through the important daily digest when installed, or through
  an important live fallback when it is not.
- [ ] Launch-start notifications, `bump --message`, and unflagged `coga slack`
  FYIs continue to use the flow webhook; automatic script-step advance remains
  silent.
- [ ] The owner-selected missing-`important_webhook` policy is explicit in code,
  tests, and `coga/sync`; it is not silently changed as a side effect of the
  routing work.
- [ ] `coga/contexts/coga/important/SKILL.md` defines the new
  “human action or high-signal outcome” bar and directly answers both the
  tune-out and duplicate-blocker-queue objections.
- [ ] `coga/contexts/coga/sync/SKILL.md` describes cadence and destination as
  separate routing axes and accurately inventories the resulting flow and
  important surfaces.
- [ ] The packaged copies at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/{important,sync}/SKILL.md`
  match their live counterparts byte-for-byte.
- [ ] Tests prove the destination for every changed emitter and preserve the
  flow/silent controls, message bodies, digest record schema, and current
  non-fatal period-state warning behavior.
- [ ] `python -m pytest` and
  `coga validate --task move-some-alerts-to-coga-important-instead-of-coga` pass.

## Proposed Shape

### Routing rule

“Important” is a destination, not a new timing tier. An event keeps its existing
cadence first; only when a Slack post is actually delivered does the routing
choice select coga-flow or coga-important.

The widened admission test is deliberately narrower than “worth knowing”:

- **Action:** a specific unresolved condition requires a human to answer,
  repair, or triage it.
- **High-signal outcome:** one completion or aggregate summarizes meaningful
  work at a natural boundary, such as the daily digest, a megalaunch drain, or
  a Dream pass.

Everything else stays in flow or stays silent. In particular, starts and
explicit FYIs provide operating awareness, while routine automatic step
movement is audit-log/git state.

### Source-derived routing matrix

| Event | Emitter / predicate | Route | Reason |
|---|---|---|---|
| `coga slack --message` | `commands/slack.py`; predicate is the existing `--important` flag | Important live only with `--important`; otherwise flow live | The sender explicitly classifies the one-off message; Coga should not infer importance from prose. |
| `bump --message` step advance | `commands/bump.py` → `bump.advance_step` with `notify_slack=True` | Flow live | It is an operator-authored FYI attached to routine movement, not inherently an action or aggregate outcome. |
| Automatic script-step advance | `commands/launch_script.py::_advance_after_script` leaves `notify_slack=False` | Silent, unchanged | Successful automatic step movement is lifecycle state; adding a post would violate this routing-only ticket. |
| `mark done` | `commands/mark.py` → `mark.mark_done` → `notify(kind="done")` | Important at delivery: digest when installed, important live fallback otherwise | A completed ticket is a high-signal outcome, but an installed digest should aggregate it once. |
| Auto-close after PR merge | `autoclose.py` → `mark.mark_done` → `notify(kind="done")` | Important at delivery: digest when installed, important live fallback otherwise | A merged and closed ticket is the same high-signal outcome regardless of who finalized it. |
| Script ticket completed | `commands/launch_script.py::_mark_script_done` → `mark.mark_done` | Important at delivery: digest when installed, important live fallback otherwise | Final script completion closes meaningful work and belongs with other done outcomes. |
| `coga block` | `commands/block.py` → `mark.mark_blocked` | Important live | The owner has a concrete unresolved ask and must act before work can resume. |
| Resumed launch exits still blocked | `commands/launch.py::_reblock_unresolved_resume` → `mark.mark_blocked` | Important live | The attempted resolution failed and the same human ask is again blocking progress. |
| Megalaunch pick exits still blocked | `megalaunch.py::_reblock_unresolved` → `mark.mark_blocked` | Important live | The queue could not clear the selected task; its owner still has to answer. |
| Blocker reminder sweep | `blocker_reminders.py::remind_blocked_tasks` | Important live | A reminder exists specifically because an unresolved human action is still outstanding. |
| Agent launch starts | `commands/launch.py` → `mark.mark_in_progress` with `slack_text` | Flow live | A start is useful operating awareness, but neither an exception nor a completed outcome. |
| Script launch starts | `commands/launch_script.py` → `mark.mark_in_progress` with `slack_text` | Flow live | A routine script start has the same awareness-only semantics as an agent start. |
| Script step fails | `commands/launch_script.py::run_script_mode` on non-zero exit | Important live | The task cannot advance and needs diagnosis or intervention. |
| Megalaunch drain summary | `commands/megalaunch.py`; only when `_drain_post_text` returns a non-empty summary | Important live | One aggregate reports the result of a deliberate work drain; empty drains remain silent. |
| Daily digest | `commands/digest.py::run_digest`; only when there are renderable records or merged commits | Important live | This is the canonical condensed outcome surface, not routine feed churn. |
| Recurring scan errors | `recurring_runner.py::_broadcast_scan` → `notify(kind="recurring-error")` | Important at delivery: digest when installed, important live fallback otherwise | Skipped scheduled work needs attention, while retaining the established daily batching cadence. |
| Recurring watchdog timeout | `recurring_runner.py::_stop_if_unfinished_after_launch` → `mark.mark_paused` → `notify` | Important at delivery: digest when installed, important live fallback otherwise | A wedged run is paused and needs intervention, but this ticket does not change its established batching cadence. |
| Declared period state did not advance | `mark.py::_warn_if_state_not_advanced`; only when stale keys exist | Important live, retaining the current best-effort/non-fatal wrapper | The next run may duplicate work unless a human repairs the high-water state. |
| Dream validate-drift summary | packaged `bootstrap/dream/tasks/validate-drift/run.py::post_slack_summary` | Important live | It is a bounded work-summary outcome from a maintenance pass, including the useful “no drift” result. |

The per-task `in_progress` mutations performed inside megalaunch remain silent;
the single drain summary is their aggregate. Draft/active/paused/retire
transitions, successful recurring creation, and `coga unblock` remain silent as
they are today.

### Delivery and API changes

1. **Teach `notification.notify` about its live fallback destination.** Add a
   keyword-only `important: bool = False` parameter in
   `src/coga/notification/__init__.py` and forward it to `post` only when no
   digest spool is installed. Do not add it to the JSONL record: records are
   delivery-neutral, and `commands/digest.py` owns the one aggregate
   destination. Update the docstring to make this asymmetry explicit.

2. **Route at semantic finalizers where the family is invariant.** In
   `src/coga/mark.py`, make `mark_blocked` post important; make `mark_done` and
   the notifying branch of `mark_paused` request an important `notify`
   fallback; and make `_warn_if_state_not_advanced` post important without
   removing its existing exception guard. Leave `mark_in_progress` on the
   default flow route. No generic routing parameter is needed on every mark
   helper: all current callers of each notifying finalizer share the decision,
   and adding caller-controlled booleans would weaken that invariant.

3. **Set direct call-site routes.** Pass `important=True` from the script
   failure path, blocker reminders, non-empty megalaunch drain summary,
   non-empty daily digest, recurring scan-error `notify` call, and packaged
   Dream validate-drift summary. Preserve the existing conditional flag in
   `commands/slack.py`. `bump.advance_step` needs no routing API change because
   its only notifying caller is the flow-only `bump --message` path and its
   automatic script caller is silent.

4. **Preserve digest behavior.** A done/error producer still appends exactly one
   record, with the current schema, details, ordering, and drain semantics.
   `commands/digest.py` posts the rendered aggregate with `important=True`.
   With no digest installed, the same producer's `notify(..., important=True)`
   uses the live important webhook. There is never both a live post and a
   spooled record for one event.

5. **Keep missing-webhook behavior explicit.** The recommended implementation
   leaves `SlackChannel.webhook_for(important=True)` fail-loud and never falls
   back to the flow webhook. That honors the existing “wrong destination is
   silent failure” argument and the repository's fail-loud principle, but it
   makes `important_webhook` operationally required when one of these automatic
   events occurs. The review-design answer below is a gate: if the owner instead
   wants automatic fallback, specify that as a separate prerequisite policy
   change rather than hiding it inside individual emitters.

### Context contract changes

Rewrite both live contexts and their packaged copies together.

- **`coga/important`:** describe coga-important as a high-signal attention
  surface, not an authoritative queue. Rebut the tune-out argument by making
  aggregation and natural boundaries the volume control: “one result for a
  body of work” qualifies, but starts, steps, routine FYIs, and raw lifecycle
  churn do not. Rebut the blocker argument by saying the ticket remains the
  only state/action queue; the important post is a cross-ticket interrupt and
  pointer to that canonical ask, not a second place where resolution is
  recorded.
- **`coga/sync`:** separate cadence (`post` live vs `notify` digest/fallback)
  from destination (flow vs important), update the live/digest inventories,
  describe `notify(important=)` fallback semantics, and update
  `important_webhook` prose from “only `coga slack --important`” to the full
  action-or-high-signal policy. Preserve the no-fallback rationale if the owner
  accepts the recommendation.
- Do not claim that `slack_important_recipient` is currently consumed. The
  routing matrix continues using existing owner/watcher rendering until the
  separate recipient work lands.

### Verification

Use the second webhook URL as the observable assertion, not only a mocked
`important=True` keyword. Keep explicit controls proving that flow posts still
use the primary URL and silent paths make no request.

- Extend `tests/test_notification.py` for `notify` with and without an installed
  digest, important-webhook failure policy, and unchanged spool record shape.
- Extend `tests/test_notification_messages.py` and the existing command/finalizer
  tests to cover manual Slack, bump, done, auto-close, block, launch starts, and
  silent script advance without changing their message snapshots.
- Extend the focused suites for script failure/completion, megalaunch summary,
  blocker reminders, digest flush, recurring scan error/watchdog, period-state
  warning, and Dream validate-drift. Notification-enabled fixtures that exercise
  new important routes must resolve both webhook URLs; retain dedicated
  one-webhook fixtures for the failure-policy test.
- Assert that the period-state warning still cannot undo a successful
  `mark done` when its important post fails.
- Run focused notification tests first, then the full suite and task-scoped
  validation.

## Out of Scope

- Wiring `slack_important_recipient` into rendering, changing the important
  alert envelope, or reviving the closed/unmerged PR #578; that is a separate
  triageability change.
- Adding alerts. In particular, automatic script-step advances and the other
  silent lifecycle transitions stay silent.
- Moving `notify` events from the daily digest to immediate delivery, posting
  per-ticket outcomes in addition to the digest, or otherwise redesigning
  live-versus-digest cadence.
- Changing message text, emojis, GIF selection, digest rendering, JSONL spool
  schema, or drain behavior.
- Inferring importance from message contents or adding new route flags such as
  `bump --important`.
- Automatically configuring downstream repositories, committing webhook
  secrets, or building a broad migration/fallback framework. If the owner
  rejects fail-loud automatic posts, that policy work should be split into a
  prerequisite ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design investigation

- Re-derived the call graph from `src/coga/`: automatic script-step advance is
  currently silent (`advance_step(..., notify_slack=False)`), despite the
  authoring-time inventory calling it a post. Keeping it silent avoids adding a
  new alert under a routing-only ticket.
- The semantic finalizers are homogeneous enough to own most routing:
  `mark_blocked` always represents an unresolved human ask; `mark_done` always
  represents an outcome; the only notifying `mark_paused` caller is the
  recurring watchdog; and `mark_in_progress` is start-awareness only.
- `notification.notify` needs an `important` fallback route, but a spooled
  record does not need a destination field: the daily digest is the delivery
  boundary and can post the aggregate to important once. This preserves the
  existing live-vs-digest timing and avoids duplicate live posts.
- The adjacent recipient work already has a closed, unmerged PR (#578) recorded
  on `coga-important/add-coga-slack-important`; current `main` still never reads
  `slack_important_recipient`. Treating that as separate remains the smallest
  scope.

## Open Questions

1. **Missing important webhook:** should automatic important routes preserve the
   current hard failure when `important_webhook` is unresolved? Recommendation:
   **yes** — keep `SlackChannel.webhook_for` unchanged, never report success after
   sending an alert to flow, and treat configuring the second webhook as an
   operational prerequisite. Cost: because the shipped template leaves the key
   commented out, an unconfigured downstream repo will fail on its first routed
   blocker/failure/digest (or no-digest outcome fallback). If automatic fallback
   is preferred, split that policy/context/config migration into a prerequisite
   ticket; it rebuts an existing fail-loud contract and is wider than a call-site
   guard.
2. **Important recipient:** confirm that consuming
   `slack_important_recipient` remains separate. Recommendation: **yes** — the
   earlier implementation PR #578 is closed without merge, and reviving or
   replacing that work changes mention/envelope semantics in addition to routing.
   This ticket should retain today's owner/watcher rendering and make the
   contexts honest about the gap.

## Scope assessment

The routing/API change, two context pairs, and focused tests fit one PR. Either
a new fallback policy or recipient/envelope wiring should be split rather than
absorbed here.
