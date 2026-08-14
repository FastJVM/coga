---
slug: remove-legacy-config-compatibility-shims
title: Remove legacy config compatibility shims
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
