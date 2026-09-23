# Superseded decisions

> **History, archived 2026-09-22.** Decisions that `coga/current-direction`
> and `coga/project-stage` recorded before the documentation-library migration
> and that later decisions replaced or reversed. They are kept so a later
> cleanup does not re-litigate them or delete a survivor twice. They are not
> instructions: current behavior is in the focused `coga/*` contracts and
> current decisions in
> [`coga/current-direction`](../contexts/coga/current-direction/SKILL.md).

## Ticket metadata and routing

- **Watchers — removed, reintroduced, removed again.** PR #43 (spec audit)
  removed multi-watcher fanout; a later change cc'd watcher names mapped under
  `[notification.slack.users]`; the ticket-format simplification (PR #784)
  removed the field, arguments, spool writes and cc rendering because no ticket
  ever populated it. The owner is the only person a post addresses.
- **`[assignees.<user>]` removed.** For three or fewer people the
  human → per-user agent nickname → agent type indirection added nothing.
  `Config.agent_type(name)` replaced `agent_type_for(user, nickname)`, and
  `user` in `coga.local.toml` became a free-form string. The later
  simplification also removed top-level `assignee:`. Reintroduce per-person
  agent configuration only when a teammate needs a different binary or auth.
- **Top-level `slug`, `human`, `assignee`, `watchers` and `script: null`
  removed** with no compatibility reader or migration tool; the stored
  population was converted in the same change and the names stay reserved.
- **`human` as an assignee role** was rewritten to `owner` in shipped workflows
  and stored snapshots and is now rejected.

## Notifications

- **Per-user Slack mentions removed, then partly restored.** The
  small-team simplification collapsed posting to a single
  `post(cfg, message)` and dropped `post_mention`/`_mention_tag`. Owner-only
  mentions later returned through `[notification.slack.users]`; the watcher
  half did not.
- **Slack became the first backend of a pluggable notification layer.** The
  driving tickets (`rename-slack-to-a-notification-system-with-pluggab`,
  `post-slack-notification-on-mode-script-failures`,
  `slack-post-ignores-http-response-so-bad-webhook-fa`) are done and pruned.

## Commands and primitives

- **`coga step` renamed `coga bump`** (spec audit, PR #43) because "step"
  collided with a workflow step. The name was changed without a compatibility
  alias.
- **`task.lock` removed** without ceremony; coordination is status-as-signal.
- **`coga dream` Typer command removed.** Dream first became an ad-hoc command,
  then a recurring template plus the default alias `dream = "recurring launch
  dream"`, so the scheduled and on-demand paths converge on `recurring/dream`.
- **`coga recurring --force` debug sandbox removed.** The old
  `<name>-dbg-<timestamp>` scratch tasks (slug-based Slack/git suppression,
  orphan reaping, fold-back to the template log) were replaced by a forced real
  run; the old force-every-template behavior of `--all` moved to `--force`.
- **Recurring task identity changed** from `tasks/recurring-<name>-<period>/`
  to the stable `recurring/<name>` ref with the period in `coga/log.md`; a
  blackboard mark was abandoned as the dedup source because any run rewriting
  that region made serviced periods re-fire.
- **`coga build` removed and restored.** It was removed with `coga project`
  (PR #691) and restored three days later (PR #701: "we want the build back
  with the skills; it was useful"); `coga project` stayed removed. Restore half
  of a removal as a scoped partial revert, not `git revert`.

## Dream and cleanup

- **Delete-only prune PRs and `## Pruned` markers retired.** Knowledge-less
  done tickets are now direct-deleted with `coga delete`; only
  knowledge-bearing deletions ride in a Retro knowledge PR.
- **Single-subagent Dream scans replaced by bounded shards** after the corpus
  outgrew one subagent and an early stop was indistinguishable from a clean
  repo.

## Skills and diagnostics

- **`eval/ticket-diagnostic` removed (2026-07-18).** A first removal on
  disuse grounds (PR #332, 2026-06-10) was reversed at review; the owner
  reopened it with new evidence. The skill was unreachable from every path, and
  the proposal to wire it in rested on a wrong premise: `coga launch
  --prompt-report` emits a layer/bytes/token table, not prompt text. The one
  useful signal — flag any layer above about 40% of the total — moved into
  `bootstrap/ticket` Step 6.
- **`detect-missing-skills` closed without a build.** A "step with no skill"
  lint would mostly produce false positives.

## Telemetry

- **Install ping rejected (2026-06).** An opt-out anonymous install ping (three
  fields, no PII) was rejected under the "Yours" principle in favor of
  PyPI/GitHub estimates. On 2026-09-20 the owner reversed the instrumentation
  ban for PostHog adoption/activity measurement and confirmed it on 2026-09-21;
  that work is owned by `coga/tasks/marketing/add-telemetry.md` and must update
  `coga/principles` when it lands. Until then the principle's text stands.

## Marketing

- The pre-registered "20 minutes a day" launch, the three-essay campaign, the
  pinned strategic fork, the channel sequence, the numeric scorecard and the
  token/time experiment are superseded; see the
  [launch-programs archive](launch-programs/README.md).
