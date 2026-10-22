---
name: coga-dev/internals/notifications
description: How Coga's notification code behaves inside — the post/notify split, fatal versus fatal=False, the preflight_post gate and its callers, audit-line gaps, credential redaction, the module behind each producer, message-format rules, the accounting rule, and how to add a notifying command.
---

# Notification internals

What a change to `src/coga/notification/`, `src/coga/slack_response.py`, or
any `post(`/`notify(` call site must not break. The user contract — surfaces,
destinations, the failure summary, the producer inventory — is
[`coga/notifications`](../../../coga/notifications/SKILL.md) and its
[producers](../../../coga/notifications/producers/SKILL.md) leaf; Slack keys
are documented in the shipped `coga.toml`.

## Surfaces in code

`notification.post` is the live path. `notification.notify` is the outcome
path: it accepts only the kinds in `OUTCOME_EVENT_KINDS` (`done`, `canceled`,
`recurring-error`) and raises `ValueError` for anything else, so it cannot
become a second general broadcaster. `post` makes one attempt with a 5-second
request timeout; backoff was removed in #56. Delivery is outbound only today;
nothing in the `post` API precludes inbound replies or slash commands later,
so do not bake in one-way assumptions.

## Two kinds of failure, one boundary

`SlackChannel` raises two things, and `notification.post` alone decides
whether either aborts the caller:

- **Configuration refusal** — `require_webhook` finds no webhook for the
  route and raises `typer.Exit(1)` after writing the remedy to stderr.
  `webhook_for` refuses an `important=True` post with no `important_webhook`
  and never reroutes it to flow.
- **Delivery miss** — a transport failure (anything in
  `slack_response.SLACK_TRANSPORT_ERRORS`: `OSError`, which includes
  `RequestException`, and `ValueError`, such as the plain `OSError` for an
  invalid CA bundle path), a revoked webhook, or a non-2xx response. `fail()`
  writes a redacted category to stderr, appends a `slack` line to
  `coga/log.md` when a `task_path` was given, then raises
  `NotificationDeliveryError`.

With the default `fatal=True` both exit 1. With `fatal=False` both are
reported and `post` returns; remaining channels are still attempted.

Posts announcing a committed transition pass `fatal=False`: `mark_blocked`,
`advance_step` (bump FYIs), `mark_done`/`mark_canceled` outcomes, the
watchdog, scan-error and period-contradiction outcomes, the autoclose retire
summary, and the recurring script-failure post. Crashing between `coga bump`'s
write and `emit_done_marker` would leave a supervised REPL waiting for its
idle backstop. Two further guards:

- `mark.py` `_warn_if_state_not_advanced` posts with the default `fatal=True`
  inside an `except Exception` guard that reports `[period-state] FYI
  broadcast failed` on stderr.
- `launch_script.py` posts a non-zero `ticket.py` exit with `fatal=False`
  (important only when the launch passed `script_failure_important`, as
  recurring runs do). Its extra `except typer.Exit` (swallow under strict
  assist, re-raise otherwise) is inert, because `post(fatal=False)` already
  returns on a configuration refusal.

## `preflight_post`: refuse before the write

`preflight_post(cfg, *, important=False)` calls `require_webhook` for every
enabled channel and raises the same `typer.Exit(1)` before any mutation. It is
the only place an unresolved webhook can still refuse a `fatal=False`
producer. Callers:

- `commands/bump.py` `bump` — a terminal bump, or a step advance with
  `--message`;
- `commands/mark.py` `done` and `canceled`;
- `launch.py` `_LaunchInvocation._run_initial_script` — the script-assist
  setup path;
- `launch_script.py` `run_script_phase` — strict assist, before `ticket.py`
  publishes a started lifecycle, wrapped in `ScriptPublicationError`;
- `autoclose.py` `_preflight_recipe_notifications` — the `before_close` hook
  of `run_autoclose_recipe`.

Ordinary `block` and launch paths, and the important script-failure,
scan-error, period-contradiction (`recurring_runner._flag_period_contradiction`)
and watchdog alerts, deliberately stay best-effort. No caller passes
`important=True` yet; use it when the gated post routes to important.

## What reaches `coga/log.md`

A configuration refusal raises before `fail()`, so it is never logged.
`record_failure=False` keeps a delivery miss on stderr only, for strict
publishers whose lease is already consumed, where a new dirty log line would
block the child's clean checkout gate. Its caller is the phone-home receipt
(`src/coga_edge/phone_home.py` `_receipt`, through the phone-home `ticket.py`
shim).

## Redaction

`requests`/`urllib3` embed the webhook URL in exception strings.
`src/coga/slack_response.py` is the only sanctioned rendering:
`format_slack_request_error(exc)` emits the class plus a fixed category (DNS,
TLS/SSL, proxy, timeout, connection, generic), never the message;
`redact_slack_webhook_credentials(text)` strips `hooks.slack.com/services/…`
paths from response bodies; `classify_slack_response(status, text)` returns
`live`, `revoked` (404 or `no_service`), or `unreachable` (5xx), and backs the
`slack-revoked`, `slack-unreachable`, and `slack-misconfigured` validate
issues. `SlackChannel.send` and `validate.probe_slack` are the only direct
webhook call sites.

## Who calls `post` or `notify`

`commands/*` front-ends often only preflight and hand a finished `slack_text`
down, so grep for the real call before editing a producer row:

- Live: `mark.py` `mark_blocked`, `mark_in_progress`, and the stale-period
  warning; `blocker_reminders.py` `remind_blocked_tasks`;
  `commands/slack.py`; `bump.py` `advance_step` (`notify_slack=True`);
  `launch_script.py`; `dream_validate_drift.py`; `commands/megalaunch.py`;
  `autoclose.py` `_report_retire_followups` and `_report_followup`;
  `coga_edge/phone_home.py` `_receipt` (`record_failure=False`);
  `recurring_autofix.py` `run_autofix` and `run_autofix_analyze_recipe`.
  Downstream sweeps on `src/coga/reminders.py` ride `coga slack`.
- Outcome: `mark.py` `mark_done`, `mark_canceled`, and `mark_paused` when the
  watchdog supplies `slack_text`; `recurring_runner._broadcast_scan`,
  `_flag_period_contradiction` (`kind="recurring-error"`), and
  `run_recurring_scan` (watchdog re-escalation).
- Silent: `branchsweep.py` writes a `## Branch Sweep` blackboard report.

**Accounting rule.** The inventory counts event kinds, not templates: one
template may span surfaces (`autoclose-merged` posts live summaries and
per-ticket outcomes). A new event kind on none of the three surfaces is an
unreviewed cadence decision. Keep the inventory in step with `coga/recurring`
when templates change.

This repo's own `coga/recurring/usage-report` routes its weekly report to
important by owner decision, so token consumption is seen on a cadence short
enough to notice a change. The user topic does not advertise that carve-out.

## Message format

Strings are built at the call sites (`commands/*.py`, `autoclose.py`, …);
`post`/`notify` never reformat. Every post gets the `[<project>] [<owner>]`
prefix from `SlackChannel.render_text`. For per-ticket posts:

- the owner is the prefix; never add an in-text `(owner: …)`;
- the title is always present: `*{slug}* "{title}"`;
- `→` is a transition and shows the prior state (`{prev} → {new}`); a
  workflow-less done post collapses to "finished";
- `:` introduces the body, `(key: value)` is an aside, and `—` is reserved
  for the trailing FYI (`bump --message`, pause reasons, retire notes);
- PR references are Slack links, `<{url}|PR #{N}>`.

`tests/test_notification_messages.py` snapshots the formats; extend it when a
string changes.

## Adding a notifying command

Decide, in order: the surface (`post`, `notify`, or silence); the destination
(important only when a human must act and no human-owned ticket already holds
the ask); and `fatal` plus preflight. Preflight only if the transition's
contract makes notification configuration an admission gate, and gate the
call on whether this invocation will actually post. Then add the event to
the producers inventory and the caller list above.
