The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: codex/slack-response-check
worktree: /tmp/relay-slack-response-check
pr: https://github.com/FastJVM/relay/pull/376
commit: 532f915

## Implementation notes
- Live notification code is now `src/relay/notification/slack.py`; `src/relay/slack.py` is a compatibility shim.
- The ticket's named `tests/test_slack.py` has been folded into `tests/test_notification.py`.
- Plan: share the existing Slack response classifier with the live Slack channel, fail loud on revoked/invalid or other non-OK webhook responses, and add a regression covering HTTP 404 with a `no_service` body plus task-log append.

## Verification
- `python -m pytest tests/test_notification.py tests/test_validate.py` in `/tmp/relay-slack-response-check`: 61 passed.
- `python -m pytest` in `/tmp/relay-slack-response-check`: 754 passed, 1 skipped.
- `PYTHONPATH=/tmp/relay-slack-response-check/src python -m relay.validate --task slack-post-ignores-http-response-so-bad-webhook-fa --json` from the primary checkout: ok_count 1, no issues.
- PR #376 is open, non-draft, mergeStateStatus CLEAN; `gh pr checks 376` reports no checks on `codex/slack-response-check`.

## Peer review (Claude, /code-review default effort)
- Ran 8 finder angles (correctness x3, removed-behavior/cross-file, reuse/simplification/efficiency, altitude, conventions). **Zero must-fix findings.**
- Correctness scan: clean. `resp` is always bound before use (the except branch's `fail()` always raises). Status-code ranges cover 2xx/3xx/4xx/404/5xx correctly; no dead/unreachable branch.
- Removed-behavior: `classify_slack_response` reproduces the old inline `probe_slack` logic branch-for-branch (404/`no_service` → revoked, 200–499 → live, else → unreachable). No invariant lost.
- Cross-file finder flagged `post()` raising `typer.Exit(1)` in non-CLI/script contexts (automerge, launch_script, skill scripts) — REFUTED: this is **pre-existing** (the network-error branch on `main` already raised `typer.Exit(1)`), not introduced here, and the ticket explicitly prescribes "raise typer.Exit(1) the same way the missing-webhook branch already does." The "previously-silent failures now fatal" finding is the intended ticket behavior, not a bug.
- Conventions/altitude/reuse: clean. New `src/relay/slack_response.py` follows the existing flat-helper pattern (atomicio.py, logfile.py, slugify.py) and removes duplication.
- Re-ran tests under python3.12 (default `python` is 3.9, no `tomllib`): `tests/test_notification.py tests/test_validate.py` → 61 passed; full suite → 754 passed, 1 skipped. No code changes needed, so nothing to commit.
- (Non-blocking latent note for future work, NOT this ticket: whether `post()` should raise `typer.Exit` vs. a domain exception in non-CLI script paths is a pre-existing design question worth revisiting separately.)

## Human review (Codex, 2026-06-17)
- Reviewed PR #376 post-peer-review diff from `/tmp/relay-slack-response-check`. No findings.
- Verified PR state after `git fetch origin`: open, non-draft, `mergeStateStatus` CLEAN, no GitHub checks configured.
- Verification rerun in feature worktree:
  - `git diff --check origin/main...HEAD`
  - `python -m pytest tests/test_notification.py tests/test_validate.py` -> 61 passed
  - `python -m pytest` -> 754 passed, 1 skipped
  - `PYTHONPATH=/tmp/relay-slack-response-check/src python -m relay.validate --task slack-post-ignores-http-response-so-bad-webhook-fa --json` from primary checkout -> ok_count 1, no issues
- Decision: merge PR #376, then run `relay automerge` from the primary checkout for task closeout.
