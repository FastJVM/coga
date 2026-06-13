The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: codex/notification-channels
worktree: /tmp/relay-notification-channels
pr: https://github.com/FastJVM/relay/pull/359

(No CI configured on this repo — `gh pr checks 359` reports no checks. Verification was local; see Self-QA + Implement result below.)

## Implementation notes

- Using a `relay.notification` package so the Slack backend has a real sibling slot for future email channels.
- Config target is `[notification]` with `channels = ["slack"]` plus `[notification.slack]`; legacy `[slack]` and `SLACK_WEBHOOK_URL` remain compatibility inputs with deprecation messaging.
- `relay slack` stays as the existing manual broadcast command, backed by the notification path.

## Implement result

- Commit: `fcc08a1` (`Introduce notification channel layer`) on `codex/notification-channels`.
- Runtime: moved notification behavior to `src/relay/notification/`; `SlackChannel` owns Slack rendering/webhook delivery; `src/relay/slack.py` is now a compatibility shim.
- Config: canonical shape is `[notification] channels = ["slack"]` plus `[notification.slack]`; legacy `[slack]` and bare `SLACK_WEBHOOK_URL` still resolve with deprecation notes.
- Docs/templates: updated live contexts, packaged bootstrap contexts/templates, README, vision, prompt text, example config, digest/Dream references, and autonomy workflow wording.
- Tests: renamed `tests/test_slack*` to `tests/test_notification*`; added channel dispatch, dedupe/empty-channel, legacy `[slack]`, and bare-env fallback coverage.

Verification:

- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider` — 721 passed, 1 skipped.
- `PYTHONPATH=/tmp/relay-notification-channels/src PYTHONDONTWRITEBYTECODE=1 python -m relay.cli validate --json` from `example/relay-os` — clean.
- `PYTHONPATH=/tmp/relay-notification-channels/src PYTHONDONTWRITEBYTECODE=1 python -m relay.cli validate --task rename-slack-to-a-notification-system-with-pluggab --json` from primary checkout — clean.
- Repo-wide validation in the feature worktree still reports unrelated pre-existing draft/broken-ref issues; task-scoped validation is clean.

---

## Self-QA

Ran `/code-review` (high effort, 7 finder angles + verify) and `/simplify`
(4 cleanup angles) against `main...HEAD` in the worktree.

**Correctness:** clean. The one borderline candidate — `post()` writing to
stderr instead of crashing when `notification_channels` is empty — is an
intentional disable path; the crash-loud semantics are preserved via
`slack_enabled` + missing-webhook → `typer.Exit(1)` in
`notification/slack.py:67-75`. All migrated semantics (crash-loud/no-retry,
enabled-by-default, `[project] [owner]` prefix, watcher cc, milestone GIFs,
mention rendering) verified intact. Compat shim re-exports `requests`
deliberately (preserves `relay.slack.requests` monkeypatch surface).

**Applied:** merged the two-pass loop in `_render_done_people`
(`notification/__init__.py`) into a single pass — behavior-identical,
flagged by 3 agents. Commit `992ad68`.

**Skipped (noted for human reviewer / follow-up):**
- config.py back-compat resolvers share loop *structure* but differ in value
  type, error messages, legacy-note handling, and the webhook's extra env
  fallback. A generic helper would thread all that through and end up more
  convoluted — agents agreed it's over-engineered for N callers. Left as-is.
- cc-trailer rendering duplicated between `SlackChannel.render_text` and
  `_cc_trailer` — different shapes (watchers list vs union-over-records) and
  different layers (channel backend vs digest renderer). Unifying now couples
  the digest renderer to the channel.
- `_channels()` returns `list[SlackChannel]`; a `Channel` protocol/ABC would
  generalize the type, but that's speculative until a second backend exists
  (explicit non-goal). The digest still emitting Slack-flavored mention
  syntax is likewise intended scope for this rename — follow-up when email
  lands.

**Verification:**
- `PYTHONPATH=src python3.12 -m pytest -q -p no:cacheprovider` — 721 passed,
  1 skipped. (Default `python` here is conda 3.9, no `tomllib`; use 3.11+.)
- example fixture `validate --json` — clean (0 issues).
