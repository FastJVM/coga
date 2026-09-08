---
slug: a-slack-repo-without-important-webhook-can-abort-t
title: A Slack repo without important_webhook can abort the recurring scan phase
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts: []
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
step: 2 (peer-review)
---

## Description

A repo that selects a Slack channel but does not configure `important_webhook` can abort the
recurring **scan phase** outright.

`SlackChannel.webhook_for` (`src/coga/notification/slack.py`) is fail-loud with no fallback when an
important webhook is requested and none is configured. `_broadcast_scan` in
`src/coga/recurring_runner.py` calls `notify(..., important=True)` **unwrapped**, so that fail-loud
raise propagates and takes the scan down before any period task runs.

Both surviving *launch* sites wrap `SystemExit`, so the blast radius is the scan phase specifically,
not recipe execution.

Decide whether an unresolved important webhook should be fatal at all. Options: fall back to the
ordinary channel, warn-and-continue, or fail fast at config-validation time instead of mid-scan —
but a misconfigured notification sink silently killing the whole sweep is the worst of the three.

## Context

Found by Dream 2026-08-24, Phase 6, while verifying an unrelated finding for PR #721.

**The original finding was wrong and this is its corrected form.** Dream Phase 2 (shard-04) reported
that the seeded `example/coga/coga.toml` enables a Slack opt-in that halts recurring runs. That
premise is false — the fixture has `channels = []`, no `[notification.slack]` table, and no
`important_webhook`, and `example/coga/coga.local.toml` is Slack-free. The PR agent rejected the fix
and left the fixture alone.

The abort path itself is partially real, but differently shaped than reported: the finding blamed
`_run_recipe_task`, which no longer exists (removed in the recurring -> `ticket.py` migration). The
live path is `_broadcast_scan`. Filed as its own ticket so the corrected version does not die with
the rejected one.

<!-- coga:blackboard -->

## Dev

branch: scan-alert-nonfatal
worktree: /home/n/Code/claude/coga-scan-alert-nonfatal

## Decision

Human chose **generalize `post(fatal=False)`** over the three alternatives
(narrow try/except at the call site, escalate validate to a hard preflight,
fall back to the flow webhook).

`notification.post` now catches the channel's configuration `typer.Exit`
alongside `NotificationDeliveryError` and re-raises it only when `fatal=True`.
`_broadcast_scan` passes `fatal=False`.

What this deliberately does *not* change: `SlackChannel.webhook_for` still
refuses to reroute an important post to the flow webhook. The reroute is the
fallback the design rejects; the crash is only how that refusal used to reach
the caller. Under `fatal=False` the alert is dropped loudly, never redirected.

Tradeoff accepted: the scan-error Slack alert is lost on a misconfigured repo.
Mitigated three ways that all already existed — each skipped template is
written to stderr by `_broadcast_scan`, `_print_table` renders them, and
`validate._important_webhook_issue` already warns
`slack-important-webhook-unresolved`.

## Findings

- **Correction to the ticket description.** `typer.Exit` is
  `click.exceptions.Exit(RuntimeError)`, **not** a `SystemExit`. So the two
  launch sites' `except SystemExit` (`recurring_runner.py:1868`, `:3159`) would
  not have caught this either — they wrap `ticket.py` `sys.exit`, a different
  failure. The blast-radius conclusion still holds for a different reason:
  `_broadcast_scan` is called at `recurring_runner.py:1591`, before
  `_print_table` and before the launch loop, so the `typer.Exit` unwinds to the
  Typer CLI and the sweep exits 1 with no period task run.
- Trigger conditions, all required: `scan.errors` non-empty **and** no digest
  spool installed (so `notify` falls back to a live `post`) **and** slack in
  `[notification].channels` **and** `enabled` **and** no resolved
  `important_webhook`.
- `preflight_post` is called with `important=False` at all six of its sites, so
  it never preflighted the important route. Left as is — widening it is the
  fail-fast option the human did not pick.

## Blast radius of the shared change

`post(fatal=False)` has these other callers, all of which now also survive an
unresolved webhook instead of crashing after their write: `bump.py:259`,
`mark.py:225,375,915,995,1091`, `autoclose.py:633`, `launch_script.py:431`.
That is the intended generalization — each announces a transition already
committed to disk, and each is fronted by a `commands/*` `preflight_post(cfg)`
that still crashes *before* the mutation.

## Changed

- `src/coga/notification/__init__.py` — `post` catches `typer.Exit` from
  `channel.send`; `post`/`notify` docstrings.
- `src/coga/notification/slack.py` — `NotificationDeliveryError` and
  `webhook_for` docstrings: the refusal is absolute, the *abort* is `post`'s
  call.
- `src/coga/recurring_runner.py` — `_broadcast_scan` passes `fatal=False`.
- `coga/contexts/coga/sync/SKILL.md` and its packaged copy under
  `src/coga/resources/templates/` (kept byte-identical): the carve-out
  paragraph, the `important_webhook` key description, the `post` implementation
  pointer, and the `notify` producer list.
- `tests/test_notification.py` —
  `test_post_missing_webhook_still_crashes_when_non_fatal` inverted and renamed
  to `..._reports_and_returns_when_non_fatal`; added
  `test_post_missing_webhook_still_crashes_when_fatal` and
  `test_important_post_without_important_webhook_never_reroutes_when_non_fatal`.
- `tests/test_notification_messages.py` — regression test
  `test_recurring_scan_error_without_important_webhook_does_not_abort`.

No `example/` fixture change: the fixture is Slack-free, and nothing here
touches task layout, prompt composition, or workflow semantics.

## Verification

- `python -m pytest` (full suite, 3.12 venv): `2 failed, 2371 passed`.
- Same command on `main` before the change: `2 failed, 2368 passed`. Identical
  two failures, +3 from the new tests.
- `coga validate --json`: runs clean of notification issues (pre-existing
  `unsynthesized-draft-blackboard` / `unfrozen-workflow` findings on unrelated
  tickets only).

## Adjacent bugs found — not fixed here

Both fail on `main` at 4271813a, untouched by this change:

- `tests/test_notification_messages.py::test_recurring_create_is_silent` —
  `IsADirectoryError` on `coga/tasks/work`. `_make_task(force_directory=True)`
  returns the task *directory*, and something downstream opens that path as a
  file. No follow-up ticket found.
- `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` — the test
  shells out to `sys.executable -m pip`, and the repo venv has no `pip`
  installed. Environmental, but the test could build with `build`/`uv` or skip
  when pip is absent.

## Next

`coga bump` from the primary checkout → `peer-review`. No push, no PR (that is
`code/open-pr`, two steps out).
