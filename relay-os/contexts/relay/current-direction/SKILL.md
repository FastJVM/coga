---
name: relay/current-direction
description: What we're building right now in relay. Recent decisions, open tickets, deferred features. Living document — updates every few weeks. Read this to avoid re-litigating closed decisions.
---

# Relay — current direction

Last updated: 2026-05-06.

## Recent decisions (Dream — ad-hoc triggering for now)

- **Dream is manual and ad-hoc for now.** Run `relay dream` to create a normal
  Dream task (`dream`, `dream-2`, etc.) and launch the cleanup pass. Dream does
  not need a weekly bucket or schedule-derived slug: it scans current Relay
  state, writes to its own blackboard, and finishes through `relay mark done`.
  Recurring scheduling stays separate until the worker pass is trusted enough
  to run unattended. Same intent for REM.

## Recent decisions (Dream and REM)

- **Dream is Relay's generic ticket cleanup pass.** It scans all tickets, runs
  fixed Relay housekeeping skills, proposes done-ticket cleanup, keeps one
  run-level summary, and surfaces context/skill/workflow drift.
- **First enabled Dream skill pass:** `validate-drift` for deterministic repo
  validation and safe file-presence repairs; `retro/done-ticket` for
  durable-knowledge extraction from completed tasks.
- **REM is repo/user-specific recurring maintenance.** It is opt-in user space:
  each repo can copy `recurring/_rem.md`, define its own cadence, scan, domain
  skills, output conventions, and review gates.
- **Dev hygiene is outside Dream.** Stale branches, tests, and other code-repo
  cleanup belong in a dev maintenance task or workflow, not the generic Dream
  cleanup pass.
- **Done-ticket cleanup is retro-first, same-PR-delete.** A done task without a
  `## Retro` marker needs Retro. An open PR adding that marker or deleting the
  exact task directory means Retro is in flight. The Retro PR records the marker
  and deletes the source task directory in the same PR; after deletion, git
  history is the audit trail.

## Recent decisions (small-team Slack simplification)

- **`slack` field on `[assignees.<name>]` removed.** With ≤3 people
  on a shared channel, plain-text posts reach everyone — per-user
  @mentions add zero signal. `slack.py` collapses to a single
  `post(cfg, message)`; `post_mention` and `_mention_tag` are gone.
  `relay panic` now posts `"<owner>: <slug> ..."` instead of
  `"<@SLACKID> — <slug> ..."`. Re-introduce per-user mentions when
  team size makes "who needs to look at this" stop being obvious
  (same logic as removing watchers).

## Recent decisions (alias mechanism)

- **`[aliases]` table in `relay.toml`.** Maps a one-word name to an
  expanded relay command (free-form string). Positional args after
  the alias name forward to the expansion. Default alias:
  `chat = "launch bootstrap/orient"`. Validated at config load:
  alias names can't collide with built-ins; first token of expansion
  must be a known built-in.
- **`relay draft` and `relay ticket` split raw scaffolding from guided
  authoring.** `relay draft` scaffolds a raw draft and posts `✨`;
  `relay create` remains a compatibility spelling. `relay ticket`
  runs the `bootstrap/ticket` interview against a new or existing
  draft/active/paused ticket. Aliases stay positional-pass-through only.
- **Aliases print their expansion to stderr.** `relay chat` prints
  `→ relay launch bootstrap/orient` before dispatching, so the
  indirection is visible. Users learn the long form by using the short
  form.

## Recent decisions (PR #43, spec audit)

12 audit threads were resolved during the spec-audit review. The
ones that affect implementation:

- **Watchers removed.** No multi-watcher fanout. `assignee` is the
  only person field surfaced in Slack messages. Re-introduce when
  team size warrants it.
- **Manual edits stay silent by design.** Editing ticket.md,
  blackboard.md, or contexts directly does NOT post to Slack and
  does NOT log. Slack is for agent-driven state transitions only.
  No post-commit hooks watching task files.
- **`relay step` renamed to `relay bump`.** The "advance" semantic
  stays; the name changed because "step" overloaded with "step in
  workflow" was confusing. `bump` derives the next step from the
  current `step:` frontmatter and always advances by one. It does
  not finish tickets — bumping past the last step (or on a no-workflow
  ticket) errors and points at `relay mark done`.
- **`relay recurring check` is the canonical entry point** for the
  cron scaffolder. Cron scripts and docs call it directly rather
  than going through `relay draft` / `scaffold_task()`.
- **Lock cleanup is human-needed by default.** `relay validate`
  reports stale locks but doesn't auto-clean. Dream's `validate-drift` skill
  classifies stale locks for human review unless a narrower skill contract has
  exact evidence that deletion is safe.
- **Control plane and data plane are fully split.** `draft` is unapproved,
  `active` is approved/queued, and `in_progress` is launched work. `relay
  launch` owns the `active` → `in_progress` start transition; `relay bump`
  owns `step:` movement and only runs while the task is `in_progress`.
  The normal boot is `relay ticket "<title>"` → review the draft →
  `relay mark active <slug>` → `relay launch <slug>`.

## Open ticket queue (audit-driven bugs)

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
6. **`post-slack-notification-on-mode-script-failures`** — depends
   on #1 being green.

## Larger ticket in flight

- **`finish-slack-integration-features`** — broader Slack
  roadmap (channel routing, threading, retry, error visibility).
  Don't scope-creep the small Slack tickets into this one;
  let them stay narrow.

## Deliberately deferred

- Inbound Slack → ticket creation. Separate Slack-as-sync ticket.
- Multi-workspace Slack. One workspace assumed for now.
- Per-user @mentions in Slack. Posts are plain text — owner name is
  in the message body. Re-add when team grows past ~3.
- Real-time sync (server backend). Git push/pull is the sync layer
  through ~5-person team size; revisit at 10+.
- `relay update-workflow` to re-snapshot a workflow into in-flight
  tickets. v1 is manual frontmatter edit.

## What this context does NOT cover

- Timeless principles — see `relay/principles`.
- The current iteration's *posture* (volatility, no real users) —
  see `relay/project-stage`.
- The mental model — see `relay/architecture`.
