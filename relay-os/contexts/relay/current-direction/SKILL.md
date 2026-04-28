---
name: relay/current-direction
description: What we're building right now in relay. Recent decisions, open tickets, deferred features. Living document — updates every few weeks. Read this to avoid re-litigating closed decisions.
---

# Relay — current direction

Last updated: 2026-04-27.

## Recent decisions (PR #43, spec audit)

12 audit threads were resolved during the spec-audit review. The
ones that affect implementation:

- **Watchers removed.** No multi-watcher fanout. `assignee` is the
  only person field that triggers Slack mention. Re-introduce when
  team size warrants it.
- **Manual edits stay silent by design.** Editing ticket.md,
  blackboard.md, or contexts directly does NOT post to Slack and
  does NOT log. Slack is for agent-driven state transitions only.
  No post-commit hooks watching task files.
- **`relay step` → `relay bump` (rename pending).** The "advance"
  semantic stays; the name changes because "step" overloaded with
  "step in workflow" was confusing. Code change not landed yet.
- **`relay create --check-recurring` is canonical.** No standalone
  `relay recurring` subcommand. Spec L996 still claims absorption
  but spec L684 is the right place.
- **Lock cleanup is the dream skill's job.** `relay validate`
  reports stale locks but doesn't auto-clean. Dream/drift removes.
- **Slack fallback for missing user IDs is a bug.** No silent
  `@<name>` plaintext fallback. Validate at config load.
- **`relay launch` auto-activates drafts.** Running launch on a
  `draft` ticket flips it to `active` and logs the transition.
  No separate `relay activate` command. Bootstrap-skill tickets
  (top-level `skill:` ref) are exempt — they stay `draft` until
  the human launches the real ticket.

## Open ticket queue (the 7 audit-driven bugs)

In suggested order:

1. **`diagnose-slack-notifications-not-firing-in-practic`** —
   blocks all other Slack work. Slack isn't actually firing in
   nick's setup. Investigate first.
2. **`reconcile-recurring-command-spec-contradiction`** —
   doc-only, fast.
3. **`make-relay-panic-exit-non-zero`** — small, isolated.
4. **`fix-relay-status-narrow-terminal-table-wrapping`** — small,
   isolated.
5. **`fail-loud-on-missing-context-or-skill-at-launch`** — touches
   compose.py + validate.
6. **`validate-slack-user-ids-at-config-load`** — config validation.
7. **`post-slack-notification-on-mode-script-failures`** — depends
   on #1 being green.

## Larger ticket in flight

- **`finish-slack-integration-features`** — broader Slack
  roadmap (channel routing, threading, retry, error visibility).
  Don't scope-creep the small Slack tickets into this one;
  let them stay narrow.

## Deliberately deferred

- Inbound Slack → ticket creation. Separate Slack-as-sync ticket.
- Multi-workspace Slack. One workspace assumed for now.
- Per-on-call routing for `relay panic`. Currently posts a single
  mention.
- Real-time sync (server backend). Git push/pull is the sync layer
  through ~5-person team size; revisit at 10+.
- `relay update-workflow` to re-snapshot a workflow into in-flight
  tickets. v1 is manual frontmatter edit.

## What this context does NOT cover

- Timeless principles — see `relay/principles`.
- The current iteration's *posture* (volatility, no real users) —
  see `relay/project-stage`.
- The mental model — see `relay/architecture`.
