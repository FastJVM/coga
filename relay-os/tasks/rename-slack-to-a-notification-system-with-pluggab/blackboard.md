The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: codex/notification-channels
worktree: /tmp/relay-notification-channels

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
