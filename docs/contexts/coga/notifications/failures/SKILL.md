---
name: coga/notifications/failures
description: What happens when a configured notification cannot be delivered or has no resolved webhook — fatal versus fatal=False posts, the preflight_post configuration gate and its callers, the best-effort exceptions and audit-line gaps, and the credential-redaction rule with its incident response.
---

# Notification failures

Applies once a channel is selected and enabled; with no channel or with the
opt-out, `post` writes one stderr line and returns
([`coga/notifications`](../SKILL.md)).

## Two kinds of failure, one boundary

`SlackChannel` raises two things, and `notification.post` is the single place
that decides whether either aborts the caller:

- **Configuration refusal** — `require_webhook` finds no webhook for the
  route and raises `typer.Exit(1)` after writing the remedy to stderr. An
  `important=True` post with no `important_webhook` is refused by
  `webhook_for`; it is **never rerouted** to flow, because a human-action
  alert in the wrong channel reported as success is worse than a crash.
- **Delivery miss** — network error, revoked webhook, or non-2xx response.
  `fail()` writes a redacted category to stderr, appends a `slack` line to
  `coga/log.md` when a `task_path` was given, then raises
  `NotificationDeliveryError`.

With the default `fatal=True` both exit the command with status 1: a rerun
reproduces a configuration error identically, so the crash is the fix. With
`fatal=False` both are reported and `post` returns; remaining channels are
still attempted. A dropped important alert under `fatal=False` is dropped,
not rerouted.

## `fatal=False`: announcing a write already on disk

Posts that announce a committed transition pass `fatal=False`: `mark_blocked`,
`advance_step` (bump FYIs), `mark_done`/`mark_canceled` outcomes, the
watchdog and scan-error outcomes, the autoclose retire summary, and the
recurring script-failure post. The markdown is the source of truth, so a
failed announcement must not decide whether the session ends — crashing
between `coga bump`'s write and `emit_done_marker` would leave a supervised
REPL waiting for its idle backstop. Git publication makes the same bargain.

Two further guards keep a broadcast from undoing a durable result:

- `mark.py` `_warn_if_state_not_advanced` posts its important warning with
  the default `fatal=True` inside an `except Exception` advisory guard that
  reports `[period-state] FYI broadcast failed` on stderr.
- `launch_script.py` posts a non-zero `ticket.py` exit with `fatal=False`
  (important only when the launch passed `script_failure_important`, as
  recurring runs do; flow otherwise). Its extra `except typer.Exit` (swallow
  under strict assist, re-raise otherwise) is inert today, because
  `post(fatal=False)` already returns on a configuration refusal.

## `preflight_post`: refuse before the write

`preflight_post(cfg, *, important=False)` calls `require_webhook` for every
enabled channel and raises the same `typer.Exit(1)` **before** any mutation,
so the ticket still holds its previous state. It is the only place an
unresolved webhook can still refuse a `fatal=False` producer. Callers:

- `commands/bump.py` `bump` — a terminal bump, or a step advance with
  `--message`, i.e. whenever this invocation will post;
- `commands/mark.py` `done` and `canceled`;
- `commands/launch.py` `_launch` — the script-assist setup path;
- `launch_script.py` `run_script_phase` — strict assist, before `ticket.py`
  publishes a started lifecycle, wrapped in `ScriptPublicationError`;
- `autoclose.py` `_preflight_recipe_notifications` — the `before_close`
  hook of `run_autoclose_recipe`.

Ordinary `block` and launch paths, and the important script-failure,
scan-error, and watchdog alerts, deliberately do not preflight and stay
best-effort. No caller currently passes `important=True`; use it when the
gated post routes to important. When adding a caller, preflight only if the
transition's contract makes notification configuration an admission gate,
and gate the call on whether this invocation will actually post.

## What reaches `coga/log.md`

The ordinary delivery-miss path appends an audit line. Two paths do not:

- a configuration refusal raises before `fail()`, so it is never logged, in
  any mode;
- `record_failure=False` keeps a delivery miss on stderr only. `post` and
  `notify` accept it for strict publishers whose exact lease is already
  consumed, where a new dirty log line would block the child's clean
  checkout gate or be swept unleased; no current caller passes it.

## Never render a raw Slack error

The webhook URL is a bearer token, and `requests`/`urllib3` embed it in
exception strings that would otherwise reach stderr and the git-tracked
`coga/log.md`. `src/coga/slack_response.py` is the only sanctioned rendering:

- `format_slack_request_error(exc)` emits the exception class plus a fixed
  category (DNS/name resolution, TLS/SSL, proxy, timeout, connection,
  generic), never the message;
- `redact_slack_webhook_credentials(text)` strips `hooks.slack.com/services/…`
  paths from every response body before it becomes detail;
- `classify_slack_response(status, text)` returns `live`, `revoked` (404 or
  `no_service`), or `unreachable` (5xx); `SlackChannel.send` and
  `validate.probe_slack` both use it (`slack-revoked`, `slack-unreachable`,
  `slack-misconfigured` issues).

`SlackChannel.send` and `probe_slack` are the only direct webhook call sites;
a new Slack caller goes through these functions.

If a webhook URL or `/services/…` path ever appears in a diagnostic, treat
it as compromised: revoke or rotate it in Slack, redact the tracked
`coga/log.md`, and inspect every reachable commit and other copies (forks,
clones, CI logs, caches). A redaction commit does not erase history;
rewriting and force-pushing published history is a separate destructive
step that needs explicit, coordinated approval and still cannot recall
existing copies.
