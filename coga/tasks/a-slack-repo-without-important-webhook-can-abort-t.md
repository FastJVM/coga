---
title: A Slack repo without important_webhook can abort the recurring scan phase
status: done
owner: nicktoper
agent: claude
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

pr: https://github.com/FastJVM/coga/pull/761
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
- `preflight_post` is called with `important=False` at all of its sites, so
  it never preflighted the important route. Left as is — widening it is the
  fail-fast option the human did not pick.

## Blast radius of the shared change

`post(fatal=False)` has these other callers, all of which now also survive an
unresolved webhook instead of crashing after their write: `bump.py:259`,
`mark.py:225,375,915,995,1091`, `autoclose.py:633`, `launch_script.py:431`.
That is the intended generalization — each announces a transition already
committed to disk. Existing `preflight_post(cfg)` gates still crash before
the mutation where enforced; several command gates are conditional on a
strict publication/assist path, rather than unconditional for every call.

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
  returns the task directory, but the fixture constructs its `TaskRef` with
  `file_form=True`; `local_period_lease` consequently reads the directory as
  the ticket file. The peer review reproduced this on the fork-point commit;
  the affected code and test are unchanged between that base and `3092d296`.
- `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` — the test
  shells out to `sys.executable -m pip`, and the repo venv has no `pip`
  installed. Environmental, but the test could build with `build`/`uv` or skip
  when pip is absent.

## Peer review — 2026-09-08

- `codex review --base main`: no actionable regressions. The reviewer ran
  799 passing relevant tests and reproduced the existing
  `test_recurring_create_is_silent` failure on the fork-point commit.
- Fetched `origin/main` and rebased onto `3092d296` without conflicts.
  The reviewed commit is now `fe9f06ac`; `git range-diff` confirms its patch
  is unchanged. No must-fix finding required a new code commit.
- Live and packaged sync contexts remain byte-identical; branch diff passes
  `git diff --check main...HEAD`.
- `coga validate --task a-slack-repo-without-important-webhook-can-abort-t --json`:
  one valid task, no issues.
- Full post-rebase command:
  `/tmp/coga-scan-alert-peer-review-venv/bin/python -m pytest` — **2372 passed,
  1 failed** in 166.91s. The sole failure is the pre-existing directory/file
  fixture mismatch described above; all changed regression tests pass.
- This Python 3.12 environment was installed editable using
  `/tmp/coga-scan-alert-peer-review-venv/bin/python -m pip install -e '.[test]'`.
  Both pip and hatchling are available, and the wheel packaging test passes.
- The feature worktree is clean and its reviewed commit is one commit ahead
  of `origin/main`.

## Open PR — 2026-09-08

- The first `coga open-pr` attempt refused the branch because `main` had
  advanced since peer review. Rebased the recorded feature worktree onto
  `main` at `387dc3a6` without conflicts; the feature commit is now `db42f80d`.
- `git range-diff fe9f06ac^..fe9f06ac main..scan-alert-nonfatal` confirms the
  reviewed patch is unchanged. The feature worktree remains clean.
- Re-ran `/tmp/coga-scan-alert-peer-review-venv/bin/python -m pytest`:
  **2323 passed, 1 failed** in 168.24s. The sole failure is the same
  pre-existing `test_recurring_create_is_silent` directory/file fixture
  mismatch. All changed regression tests and packaging tests pass.
- `coga validate --task a-slack-repo-without-important-webhook-can-abort-t --json`
  reports one valid task and no issues. `git diff --check main...HEAD` and
  `cmp coga/contexts/coga/sync/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`
  pass in the feature worktree.
- `coga open-pr a-slack-repo-without-important-webhook-can-abort-t` succeeded
  on retry and recorded https://github.com/FastJVM/coga/pull/761 under `## Dev`.
  `gh pr view 761` confirms it is open, ready for review, and mergeable, with
  `main` as base and `db42f80d` as head. The published description includes
  the refreshed test result; both checkouts were clean after publication.

## PR

Keep a recurring sweep running when its scan-error alert cannot resolve the
configured Slack `important_webhook`. `post(fatal=False)` now reports
configuration refusals on stderr alongside delivery failures, and the scan
summary opts into that behavior. Strict posts retain exit 1; important alerts
are never redirected to the ordinary webhook.

Update the live and packaged sync contexts together, with regression coverage
for missing ordinary/important webhooks and the recurring scan fallback.

Test plan: `/tmp/coga-scan-alert-peer-review-venv/bin/python -m pytest` — 2323 passed, 1 pre-existing failure (`test_recurring_create_is_silent`, reproduced on base); `coga validate --task a-slack-repo-without-important-webhook-can-abort-t --json`, `git diff --check main...HEAD`, and `cmp coga/contexts/coga/sync/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md` pass.

## Next

Owner review of PR #761 is next. The known test fixture failure is documented
above and in the PR; the fix and its regression coverage are ready for review.
