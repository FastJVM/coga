---
name: relay/current-direction
description: What we're building right now in relay. Recent decisions, open tickets, deferred features. Living document — updates every few weeks. Read this to avoid re-litigating closed decisions.
---

# Relay — current direction

Last updated: 2026-05-06.

## Recent decisions (Dream — manual triggering for now)

- **Recurring tasks are run manually, not scheduled.** No `weekly-dream.md`
  template gets vendored into `relay-os/recurring/` yet, and no crontab
  entry calls `scripts/cron.sh`. To run Dream, invoke
  `relay-os/scripts/dream-run.sh` from the repo root — it scaffolds a
  fresh `dream-run-<timestamp>` task wired to the `bootstrap/dream-run`
  workflow and launches it. Same intent for REM (no manual script yet —
  copy the Dream pattern when needed). Wire up the schedule later, once
  the worker pass is shaken out and we trust an unattended Monday
  morning run.

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
- **Done-ticket cleanup is retro-first, delete-second.** A done task without a
  `## Retro` marker needs Retro. An open PR adding that marker means Retro is
  in flight. A processed marker means the task can be deleted under the worker
  contract; after deletion, git history is the audit trail.

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
  the alias name forward to the expansion. Default aliases:
  `chat = "launch bootstrap/orient"` and
  `create = "launch bootstrap/ticket"`. Validated at config load:
  alias names can't collide with built-ins; first token of expansion
  must be a known built-in.
- **`relay create` is no longer a Python command.** It's now an alias.
  Its `scaffold_task()` Python helper moved to `src/relay/scaffold.py`
  and is shared by `launch`'s factory path and the recurring scaffolder.
  The `--description` and `--no-launch` flags are gone (aliases are
  positional pass-through only); use the `scaffold_task()` Python API
  for scripted use.
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
  workflow" was confusing. The new command takes no positional arg —
  it derives the next step from the current `step:` frontmatter and
  always advances by one. Bumping past the last step marks `done`.
- **`relay recurring check` is the canonical entry point** for the
  cron scaffolder. Reverses the earlier "`relay create --check-recurring`
  is canonical" call: once `relay create` became a thin alias, hanging
  the recurring flag on it stopped making sense. Cron scripts and docs
  now call `relay recurring check` directly.
- **Lock cleanup is human-needed by default.** `relay validate`
  reports stale locks but doesn't auto-clean. Dream's `validate-drift` skill
  classifies stale locks for human review unless a narrower skill contract has
  exact evidence that deletion is safe.
- **`relay launch` auto-activates drafts.** Running launch on a
  `draft` ticket flips it to `active` and logs the transition.
  No separate `relay activate` command. Bootstrap-skill tickets
  (top-level `skill:` ref) are exempt — they stay `draft` until
  the human launches the real ticket.

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
