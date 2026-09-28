---
title: Treat non-RequestException Slack send errors as delivery misses
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (pr)
---

## Description

## What broke

On the 2026-09-22 10:18 sweep, `recurring/autoclose-merged` crashed with an uncaught `OSError`. The runner treated that as a stop condition, so `recurring/upstream-coga` and `recurring/blocker-reminders` were admitted as due but never launched. The run record shows:

- `recurring/autoclose-merged`: no launch outcome was recorded; an unhandled OSError stopped the sweep
- 2 of 5 due task(s) never launched after recurring/autoclose-merged
- `coga/log.md`: `[recurring/autoclose-merged] [system] script exited with code 1`

The traceback in `coga/tasks/recurring/autoclose-merged/ticket.md` shows a Slack post that failed and should not have been fatal:

```
autoclose.py run_autoclose_recipe -> sweep_merged -> _sweep_merged_into -> _try_bump_one
  -> mark.py mark_done -> announce -> notification.notify -> post
  -> notification/slack.py:140 send -> requests.post(...)
OSError: Could not find a suitable TLS CA certificate bundle, invalid path:
  /home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/certifi/cacert.pem
```

The error then happened a second time. `run_autoclose_recipe`'s `except BaseException:` handler calls `_report_retire_followups`, which posts to Slack again at `autoclose.py:993` with `fatal=False`. That post raised the same `OSError` from `slack.py:140` and replaced the original exception. Because the sweep died partway, checkout disposal was also skipped ("the sweep failed before checkout disposal ran"). At least one ticket (`the-ticket-interview-never-asks-what-done-means`) was already bumped to `done` on disk before the crash.

## Root cause

In `src/coga/notification/slack.py` (`send`, around line 140), `requests.post` is wrapped only in `except requests.RequestException`. `requests` raises a plain `OSError` from `HTTPAdapter.cert_verify` when the CA bundle path is invalid, and that is not a `RequestException`. So the error skips `fail(...)`, is never turned into `NotificationDeliveryError`, and gets past the `fatal=False` handling in `notification.post` (`src/coga/notification/__init__.py`, around line 96). The docstring there promises that an undeliverable message must not abort work that is already on disk. That promise breaks for any transport error outside the `RequestException` hierarchy.

The trigger was environmental: the installed `certifi` is missing its `cacert.pem`. But one broken alert sink should not be able to kill autoclose and every later recurring task.

## What a fix must do

1. In `SlackChannel.send`, catch `OSError` (and ideally `ValueError`, which `requests` raises for some malformed-URL and adapter cases) alongside `requests.RequestException`. Route them through the same `fail(...)` path, so they are reported to stderr, audited in `log.md` when task-scoped, and raised as `NotificationDeliveryError`. The `fatal=True` caller should still exit 1, and a `fatal=False` caller should carry on.
2. Consider a defensive layer in `notification.post`: under `fatal=False`, turn any unexpected `Exception` from `channel.send` into a reported delivery miss, so a future transport bug can't take down a sweep. Also check `preflight_post` / `_preflight_recipe_notifications` to see whether a preflight should catch a broken TLS setup before the mutation.
3. Add tests in `tests/` (e.g. `tests/test_notification.py` / `tests/test_autoclose.py`) that monkeypatch `requests.post` to raise `OSError("Could not find a suitable TLS CA certificate bundle ...")` and check that:
   - `post(..., fatal=False)` returns without raising and logs the miss
   - `run_autoclose_recipe` finishes its sweep, runs checkout disposal, and does not exit via an uncaught exception
4. If the `notification` context or skill describes delivery-failure semantics, update it to say that any transport-level failure counts as a delivery miss.

Separately, the operator should reinstall the uv tool env (`uv tool install --reinstall coga`) to restore `certifi/cacert.pem`. That fixes this machine, not the code.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/911
branch: slack-oserror-delivery-miss

Plan: widen `SlackChannel.send`'s transport catch to `(requests.RequestException, OSError, ValueError)` so every transport failure goes through `fail(...)`, and add regression tests for `post(fatal=False)` and the autoclose sweep.

## Implement handoff

- Confirmed diagnosis against code: `notification/slack.py` `SlackChannel.send` caught only `requests.RequestException`; the plain `OSError` from `requests`' CA-bundle check escaped `fail(...)` and `notification.post`'s `NotificationDeliveryError` handling.
- Fix: `send` now catches `(requests.RequestException, OSError, ValueError)` → same `fail(...)` path (stderr, `log.md`, `NotificationDeliveryError`). `slack_response.format_slack_request_error` annotation widened to `Exception` (it only uses the type and message hints, so redaction is unchanged; an `OSError` whose message mentions the certificate falls in the "TLS/SSL failure" category).
- Tests: `tests/test_notification.py` `test_post_non_request_exception_is_a_non_fatal_delivery_miss` (OSError + ValueError) and `..._still_crashes_when_fatal`; `tests/test_autoclose_dispose.py` `test_recipe_finishes_when_every_slack_post_raises_a_non_request_oserror` (rc 0, ticket done, worktree and branch disposed). All 4 failed before the fix and pass after it. Full suite: 3054 passed.
- Docs: `coga/notifications/failures` topic (canonical + packaged twin) now defines a delivery miss as any transport failure.
- Decisions, with what they give up:
  - Did not add a catch-all `except Exception` in `notification.post`: it would also hide real programming bugs in channels. The widened catch covers the whole `requests` transport surface, since `RequestException` is itself an `OSError`.
  - No TLS preflight in `preflight_post`: catching a broken CA bundle up front would need a network probe or reaching into certifi internals. That is the wrong layer for a configuration gate, and the delivery miss is now non-fatal anyway.
- ~~Adjacent, not fixed here~~ Fixed in self-qa (see below): `src/coga/validate.py` `probe_slack` had the same `except requests.RequestException` shape, so `coga validate` with a broken CA bundle would crash instead of reporting `slack-unreachable`.
- Operator action (machine, not code): `uv tool install --reinstall coga` to restore `certifi/cacert.pem`.

## Self-QA

- Review form: `/code-review` (forked skill, default effort) against `main...slack-oserror-delivery-miss`: **returned**. Plus `/simplify` with 4 parallel agents (reuse, simplification, efficiency, altitude): **all returned**. Nothing is still in flight.
- `/code-review`: one finding. `validate.probe_slack` still caught only `RequestException`, but the failures topic says it shares the same contract (a bad CA bundle would crash `coga validate`). Fixed.
- `/simplify`: altitude found the same drift (the error family was defined inline at one of two call sites). Reuse found that the new notification tests duplicated existing ones. Simplification found that `RequestException` in the tuple was redundant (it is already an `OSError`), plus an unwrapped docs line, a long comment and an extra blank line. Efficiency found nothing.
- Applied in commit `6da89af04`:
  - Added `slack_response.SLACK_TRANSPORT_ERRORS = (OSError, ValueError)`, caught in both `SlackChannel.send` and `probe_slack`.
  - Parametrized the existing `test_post_failure_crashes`, `test_post_failure_non_fatal_reports_and_returns` and `test_probe_slack_unreachable` over ConnectionError / CA-bundle OSError / ValueError, replacing the duplicates. The new `probe_slack` cases fail without the fix.
  - Rewrapped the failures topic in both twins and pointed it at the constant; trimmed the comment.
- Skipped: the optional `_raise(exc)` test helper (nit).
- No manual-only surfaces were touched: stderr/log only.
- Tests: `.venv/bin/python -m pytest` gives 3057 passed. The system `python` lacks `tomlkit`, which is an environment issue, not a finding.
