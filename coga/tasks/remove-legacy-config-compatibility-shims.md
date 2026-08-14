---
slug: remove-legacy-config-compatibility-shims
title: Remove legacy config compatibility shims
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/project-stage
- coga/sync
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

Delete the three silent config-compatibility shims. They accept a
superseded spelling and keep working, surfacing only a `coga validate` warning
the operator has to remember to run — that is exactly the "silent wrong-ish
answer" failure mode principle 6 forbids, and `coga/project-stage` says
compatibility is migration-only with a bias toward deletion. There are no real
users; a handful of keys is cheap to re-type.

Remove all three, plus every test, doc, template, and context line that
describes them. After this change the only spelling that works is the current
one, and the old one fails loud at config load.

1. **Legacy top-level `[slack]` table** — `src/coga/config.py`.
   `_ALLOWED_LEGACY_SLACK_KEYS`, the `shared.get("slack")` / `local.get("slack")`
   reads (~lines 249-250, 263-264), the `[slack]` branch in
   `_reject_unknown_sections` (~452), and the `*_legacy` parameter threaded
   through `_parse_notification_slack` → `_resolve_notification_slack_webhook`,
   `_resolve_notification_slack_enabled`, `_parse_notification_slack_gifs`,
   `_parse_notification_slack_users`, and `_slack_opt_in_present`. Dropping the
   parameter collapses a lot of plumbing — that simplification is a goal of the
   ticket, not a side effect. `_ALLOWED_SLACK_KEYS` becomes a plain literal set
   rather than `_ALLOWED_LEGACY_SLACK_KEYS | {...}`, which also retires the
   comment at ~401-404 explaining why the two sets are kept distinct.
2. **Bare `SLACK_WEBHOOK_URL` env fallback** — the final branch of
   `_resolve_notification_slack_webhook`. A repo must declare
   `webhook = "env:SLACK_WEBHOOK_URL"` explicitly.
3. **Legacy `create` alias drop** — `LEGACY_ALIASES` and the `warn_legacy`
   branch in `aliases.validate_aliases` (`src/coga/aliases.py`). With it gone,
   `create = "launch bootstrap/ticket"` in a `coga.toml` hits the existing
   built-in-collision `ConfigError`, which is the fail-loud outcome we want.
   Drop the now-unused `warn_legacy` keyword from every call site.

Once all three are gone, `Config.notification_deprecation_notes` has no
producer: delete the field and the `notification-deprecated-config` warn issue
in `validate.py` (~1114-1122).

## Context

- **Why now**: raised on PR #685, where the legacy allowlist prompted "why even
  allow legacy slack key???". `coga/project-stage` sanctions these three as
  "narrow upgrade aids for configs Coga itself previously wrote", but the same
  context says bias toward deletion, and we are pre-product with testers only.
  Retiring the aid is the intended end state, not a reversal.
- **Keep the loud rejections.** The tailored migration *errors* — top-level
  `[assignees]`, a `[secrets]` table in `coga.local.toml`, and the removed
  `[agents.<name>]` keys (`auto`, `skip_permissions`, `skip_permissions_argv`) —
  are **not** in scope. They already fail loud with actionable guidance; deleting
  them would only downgrade a helpful error into a generic unknown-key message.
  Same fail-fast outcome, worse legibility. Leave them exactly as they are,
  including their run-before-the-generic-check ordering.
- **Sequencing**: PR #685 (`drop important_recipient`) edits the same allowlist
  region of `config.py`. Land or close #685 first, then rebase — do not race it.
- **Surfaces to sweep** (search for `[slack]`, `SLACK_WEBHOOK_URL`, `legacy`,
  `deprecat`): `src/coga/config.py`, `src/coga/aliases.py`,
  `src/coga/validate.py`, `coga/contexts/coga/sync/SKILL.md`,
  `coga/contexts/coga/project-stage/SKILL.md` (the paragraph naming these as
  shipped upgrade aids must be updated — it will otherwise describe code that
  no longer exists), `docs/` , `coga/coga.toml`, `example/coga/`, and both the
  packaged templates under `src/coga/resources/templates/coga/` and their live
  repo copies (CLAUDE.md requires keeping those in sync).
- **Config check**: this repo's own `coga/coga.toml` already uses
  `[notification.slack].webhook = "env:SLACK_WEBHOOK_URL"` and has no `[slack]`
  table or `create` alias, so no local migration is needed here. Verify the
  seeded `example/coga/` fixture the same way before assuming it is clean.
- **Tests**: `tests/test_notification.py` and the config/alias suites carry
  cases asserting the legacy paths *work*. Those become cases asserting they
  now **fail loud** — do not just delete them. Full suite is
  `python3.12 -m pytest` (the repo `.venv` has no pytest and default `python`
  is 3.9).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implement

- Plan: remove the three silent compatibility paths, convert their positive
  tests to fail-loud regressions, sweep durable docs/templates/fixtures, then
  run targeted tests, the full Python 3.12 suite, and scoped fixture validation.
- Sequencing gate: PR #685 (`drop-important-recipient`) merged into `main` on
  2026-08-13, so this change can proceed from a refreshed `origin/main`.
- Primary-checkout baseline: `main`; the only pre-existing working-tree change
  is the launch-generated `coga/log.md` append, which will be preserved.
- Post-merge finding: PR #685 already landed item 1 in commit `19c39a1f`
  (`Remove legacy slack config compatibility`): top-level `[slack]` no longer
  feeds any resolver, both shared and local forms raise actionable
  `ConfigError`s, and regression coverage asserts those failures. Preserve that
  merged implementation; this branch completes items 2 and 3 plus the dead
  deprecation-note cleanup and documentation sweep.
- Decision: a bare exported `SLACK_WEBHOOK_URL` without an explicit
  `[notification.slack].webhook` key will raise an actionable `ConfigError`.
  Silently ignoring the variable would leave operators believing Slack was
  configured while notifications were disabled, contrary to the ticket's
  fail-loud acceptance.
- Implemented: removed the bare-env channel inference/webhook fallback, the
  `notification_deprecation_notes` field and validation warning, and the
  `LEGACY_ALIASES`/`warn_legacy` bypass. The exact retired `create` alias now
  reaches the ordinary built-in-collision error. Updated live and packaged
  sync contexts, config templates, project-stage posture, and the CLI extension
  audit.
- Test harness: stopped globally exporting the retired bare key. Canonically
  declared test webhook references still receive a fake resolver value; tests
  for missing webhooks use a distinct explicitly unset reference.
- Verification so far: targeted config/notification/alias/validation suites
  pass (249 tests); seeded `example/coga/` validation reports two OK tasks and
  zero issues. The first full run reached 1740 passed / 1 skipped with one
  harness-specific launch failure; that test was corrected and passes alone.
  Final full suite: 1741 passed / 1 skipped. After `origin/main` advanced, the
  branch rebased cleanly onto `31c95237` and the post-rebase full suite passed
  again with the same result. Scoped task validation also reports one OK task
  and zero issues.
- Commit: `7562229f` (`Remove legacy config compatibility shims`). Worktree is
  clean and `origin/main` is an ancestor of the branch. No push or PR was made.

## Peer review

- `codex review --base main` reported one P2 must-fix: the retired `create`
  alias collision escapes the existing `coga recurring --all` broken-config
  exemption, so starting a cross-repo sweep from a legacy checkout aborts the
  parent instead of letting the child be classified as unconfigured. Plan:
  apply the same narrow recovery exemption to alias-validation failures while
  retaining the hard collision for ordinary commands, and add dispatch-level
  regressions.
- Fixed: `cli.main` now discards an invalid current-repo alias map only for the
  cross-repo `recurring --all` parent and dispatches with built-in defaults;
  ordinary commands retain the collision error. Added a regression for the
  formerly shipped `create` alias. Focused aliases: 29 passed. Pre-rebase full
  suite: 1742 passed / 1 skipped. Review-fix commit: `c2a05ed2`.
- Freshness: fetched `origin/main` and rebased unconditionally onto `8d3988cd`;
  no conflicts. Rebased commits are `3a487338` (implementation) and `6f5054e2`
  (peer-review fix). The live and packaged `coga/sync` contexts remain
  byte-identical, `git diff --check` is clean, and the post-rebase full suite is
  1742 passed / 1 skipped.
- Final validation: scoped task validation reports one OK task and zero issues;
  seeded `example/coga/` validation (with the intentionally retired bare env
  spelling unset) reports two OK tasks and zero issues.

## PR

- Remove the bare `SLACK_WEBHOOK_URL` fallback and its deprecation-note
  plumbing, requiring an explicit `[notification.slack].webhook` declaration.
- Treat the retired `create = "launch bootstrap/ticket"` alias as an ordinary
  built-in collision while preserving cross-repo scheduler isolation from an
  invalid current checkout.
- Align shipped config/context templates and durable docs, and convert legacy
  success tests into fail-loud regressions.

Test plan: `python3.12 -m pytest` (1742 passed, 1 skipped).

## Dev

pr: https://github.com/FastJVM/coga/pull/692
branch: remove-legacy-config-shims
worktree: /tmp/coga-remove-legacy-config-shims
