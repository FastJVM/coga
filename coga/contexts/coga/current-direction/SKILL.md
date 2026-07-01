---
name: coga/current-direction
description: What we're building right now in coga. Recent decisions, open tickets, deferred features. Living document — updates every few weeks. Read this to avoid re-litigating closed decisions.
---

# Coga — current direction

Last updated: 2026-06-13.

## Current redesign (recurring lifecycle and identity)

- **Recurring runs use a stable path-qualified task ref.** The current direction is
  `coga/tasks/recurring/<name>/` (`recurring/<name>` in CLI/status/Slack),
  not `tasks/recurring-<name>-<period>/`. The `recurring/` directory is the
  namespace/identity marker; the schedule period lives in the template
  blackboard as a single overwritten `last_serviced_period` line. The template
  the repo-global `coga/log.md` remains append-only human history, not the dedup source.

- **The lifecycle stays ordinary and Dream owns cleanup.** `coga recurring`
  creates a normal `active` task, `coga launch` moves it through the usual
  ticket lifecycle, and a completed run sits as `status: done` until Dream's
  retro pass direct-deletes it. Since the instantiated task is deleted after a
  completed run, a leftover `tasks/recurring/<name>/` directory is the orphan
  signal: `in_progress` is resumed before fresh period work, and `paused` stays
  human-parked. A missing task dir plus `last_serviced_period >= current
  period_key` means this period already ran.

- **`coga recurring --all` is a forced real run, not a debug sandbox.** The
  old `<name>-dbg-<timestamp>` scratch machinery (slug-based Slack/git
  suppression, orphan reaping, fold-back-to-template-log) is gone. `--all` now
  get-or-creates and launches each template's real `recurring/<name>` task,
  bypassing only the schedule and the status filter — every other effect (Slack,
  spool drain, git sync, `last_serviced_period` advance) is identical to a bare
  sweep.

## Open rename (workflow → playbook)

- **The `workflow` primitive is being renamed to `playbook`.** Ticket:
  `rename-workflow-primitive-to-playbook` (draft, `code/design-then-implement`).
  Same motive as the earlier `coga step → coga bump` rename below: the name
  mislabels the concept. "Workflow" imports the romantic, absorption-camp
  connotation (*the automation runs itself* — n8n/Zapier/CI), which is the
  opposite of what the primitive is: a sequence of **operator handoffs**
  (`assignee: agent | human | owner`) with a human gate in the step list. The
  product is literally a *coga* (baton between runners); "playbook" names the
  ordered-plays-with-handoffs shape without the runs-itself baggage and pairs
  with `skills`/`contexts`. It touches a reserved frontmatter key, so it needs
  a design pass (alias-vs-migration for live tickets) before the mechanical
  rename — don't hand-edit the `workflow:` key in contexts ahead of the code
  change. Until merged, `workflow` is still the canonical term everywhere.

## Recent decisions (design-then-implement workflow)

- **A thin ticket gets designed before it gets built.** The
  `code/design-then-implement` workflow adds two steps in front of the
  normal `implement → open-pr → review` flow: an agent `design` step
  (skill `code/design`) that writes Description, Acceptance Criteria,
  Proposed Shape, and Out of Scope into the ticket, and an owner
  `review-design` gate to approve that spec before any code is written.
  Use it when a ticket arrives as one or two sentences; use
  `code/with-review` when the spec is already clear. The design step
  writes no code — its only output is the fleshed-out ticket plus open
  questions on the blackboard.

## Recent decisions (missing-skill detection)

- **Capability-gap detection stays judgment-based — no validate lint.**
  "Referenced-but-absent" skills are already fully covered: `coga validate`
  emits `broken-skill` for any ticket- or step-level `skill:` ref with no
  file, and `compose.py` hard-fails at launch instead of silently dropping
  the layer. The other sense — a skill that *should* exist but isn't
  referenced anywhere — is not statically detectable; a "step with no skill"
  lint would be a false-positive machine (most steps legitimately have no
  skill). The two honest detectors are the `bootstrap/ticket` step-4
  interview gap point at authoring time (which now routes through
  `bootstrap/import` before hand-writing) and Dream/retro's cross-ticket
  view (recurring hand-rolled process in done tickets → propose a skill or
  import). No programmatic handoff to the import pass — a human reading
  `coga validate` is enough. Decision closed the `detect-missing-skills`
  ticket (deleted without a build).

## Recent decisions (eval/ticket-diagnostic stays)

- **The bundled `eval/ticket-diagnostic` skill is kept.** Its removal was
  fully implemented and PR'd on disuse grounds (PR #332, 2026-06-10), then
  reversed at the human review step — the owner wants the skill retained.
  The PR was closed unmerged and the branch deleted; the packaged copy at
  `src/coga/resources/templates/coga/bootstrap/skills/eval/ticket-diagnostic/`
  stays on main (no live `coga/skills/eval/` override exists). Do not
  re-propose deleting it on "unused" grounds without a fresh human decision.

## Recent decisions (Dream — recurring template plus an alias)

- **Dream is a recurring task template plus an alias.** The standalone
  `coga dream` Typer command is gone. Dream now ships as
  `coga/recurring/dream/` — an ordinary recurring template. `coga
  recurring` creates and launches it when its weekly schedule is due;
  `coga dream` is a default alias for `recurring launch dream`, which
  creates and launches it on demand through the same path. The task ref is
  now `recurring/dream`, so the scheduled and on-demand paths converge on one
  task. This reverses the earlier "ad-hoc command" decision: there was
  nothing left in a dedicated command worth keeping once the workers became
  skills.
- **`coga recurring launch <name>` is the on-demand recurring entry point.**
  It creates one named template now, ignoring its schedule, with the same
  stable path-qualified task ref a bare `coga recurring` produces, then
  launches the task.

## Recent decisions (Dream and REM)

- **Dream is Coga's generic ticket cleanup pass.** It scans all tickets, runs
  fixed Coga housekeeping skills, proposes done-ticket cleanup, keeps one
  run-level summary, and surfaces context/skill/workflow drift.
- **First enabled Dream skill pass:** `validate-drift` for deterministic repo
  validation and safe file-presence repairs; `retro/done-ticket` for batched
  durable-knowledge extraction from completed tasks. Dream loads the
  context/skill corpus once per run, processes every eligible done ticket with
  a running knowledge delta, batches them into coherent PRs of at most five
  source tickets each, and keeps each knowledge PR small enough to describe
  with one clear title.
- **REM is repo/user-specific recurring maintenance.** It is opt-in user space:
  each repo can copy `recurring/_rem/`, define its own cadence, scan, domain
  skills, output conventions, and review gates.
- **Dev hygiene is outside Dream.** Stale branches, tests, and other code-repo
  cleanup belong in a dev maintenance task or workflow, not the generic Dream
  cleanup pass.
- **Done-ticket cleanup is retro-first, and every processed done ticket is
  deleted — knowledge-bearing tickets in a PR, knowledge-less tickets
  directly.** A done task whose directory still exists, with no open PR adding
  its `## Retro` marker or deleting it, is eligible for Retro. If Retro extracts
  durable knowledge, its PR records the marker, updates the knowledge base, and
  deletes the source task directory in the same PR — so a human can reject or
  edit the knowledge change and the deletion together, atomically. If Retro
  finds no new durable knowledge, there is no PR to bundle the deletion into, so
  the ticket is **direct-deleted** via `coga delete <slug>` (working-tree
  `git rm` plus a direct `Ticket: <slug> — deleted` commit); no marker, no
  `## Pruned` section, no delete-only prune PR. After deletion git history is the
  audit trail and recovery is via `git restore`. This replaces the earlier model
  that bundled every deletion — including knowledge-less ones — into a knowledge
  PR or a single delete-only prune PR. Retro never leaves a processed done
  ticket on disk and never opens a marker-only PR.

## Recent decisions (assignees flattened out)

- **`[assignees.<user>]` removed entirely.** For ≤3 people, the
  human → per-user-agent-nickname → agent-type indirection earned
  nothing — every team member's map was identical. A ticket's
  `assignee:` now names an `[agents.<type>]` block directly
  (e.g. `claude`, `codex`) or a human name (routing only; not
  launchable). `Config.agent_type(name)` replaces the old
  `agent_type_for(user, nickname)`. `coga.local.toml`'s
  `user = "name"` is a free-form string — no registry to validate
  against. Re-introduce per-person agent configs when one teammate
  genuinely needs a different binary or auth from another.

## Recent decisions (small-team Slack simplification)

- **`slack` field on `[assignees.<name>]` removed.** (Historical: the
  `[assignees]` table itself is now gone — see above.) With ≤3 people
  on a shared channel, plain-text posts reach everyone — per-user
  @mentions add zero signal. At the time, `slack.py` collapsed to a
  single `post(cfg, message)` and `post_mention` / `_mention_tag` were
  dropped.
- **Per-user @mentions since re-introduced.** The prediction above
  held: `notification.post(cfg, message, *, owner=..., watchers=...)`
  dispatches through the Slack backend, whose mention helper renders any name
  mapped in `[notification.slack.users]` as a real `<@U…>` ping — owner
  inline, watchers cc'd in a trailer. Posts ping the ticket owner and watchers
  again; see `coga/sync` for the current behavior.

## Recent decisions (alias mechanism)

- **`[aliases]` table in `coga.toml`.** Maps a one-word name to an
  expanded coga command (free-form string). Positional args after
  the alias name forward to the expansion. Default alias:
  `chat = "launch bootstrap/orient"`. Validated at config load:
  alias names can't collide with built-ins; first token of expansion
  must be a known built-in.
- **`coga create` and `coga ticket` split raw creating from guided
  authoring.** `coga create` creates a raw draft and posts `✨`.
  `coga ticket` runs the `bootstrap/ticket` interview against a new or
  existing draft/active/paused ticket. Aliases stay positional-pass-through
  only.
- **Aliases print their expansion to stderr.** `coga chat` prints
  `→ coga launch bootstrap/orient` before dispatching, so the
  indirection is visible. Users learn the long form by using the short
  form.

## Recent decisions (PR #43, spec audit)

12 audit threads were resolved during the spec-audit review. The
ones that affect implementation:

- **Watchers removed.** No multi-watcher fanout. `assignee` is the
  only person field surfaced in Slack messages. Re-introduce when
  team size warrants it.
- **Manual edits stay silent by design.** Editing ticket.md,
  the blackboard region, or contexts directly does NOT post to Slack and
  does NOT log. Slack is for agent-driven state transitions only.
  No post-commit hooks watching task files.
- **`coga step` renamed to `coga bump`.** The "advance" semantic
  stays; the name changed because "step" overloaded with "step in
  workflow" was confusing. `bump` derives the next step from the
  current `step:` frontmatter and normally advances by one. Humans may
  rewind in-progress workflow tasks to an earlier step with `--to` or
  `--backward`; agents still block instead of going backward. `bump` does
  not finish tickets — bumping past the last step (or on a no-workflow
  ticket) errors and points at `coga mark done`.
- **`coga recurring` is the canonical entry point** for the recurring
  creator. It scans templates, creates the current period's task for
  each, and launches the due ones sequentially — current period only, no
  backlog of missed periods. Coga v1 ships no scheduler wrapper; operators
  invoke `coga recurring` directly when they want a sweep.
- **Control plane and data plane are fully split.** `draft` is unapproved,
  `active` is approved/queued, and `in_progress` is launched work. `coga
  launch` owns the `active` → `in_progress` start transition; `coga bump`
  owns `step:` movement and only runs while the task is `in_progress`.
  The normal boot is `coga ticket "<title>"` → review the draft →
  `coga launch <slug>`, which activates the draft inline as it starts work.

## Notification layer (Slack) — shipped

The earlier audit-driven bug queue and the Slack-notification queue have both
been worked off. The notification-layer rename shipped: Slack is now the
notification layer (a pluggable notification system), and the tickets that
drove it are done and pruned — `rename-slack-to-a-notification-system-with-pluggab`,
`post-slack-notification-on-mode-script-failures`, and
`slack-post-ignores-http-response-so-bad-webhook-fa` are all completed and no
longer on disk.

The only Slack idea still parked is a v2 draft:
`use-slack-as-a-sync-channel-for-tickets` — inbound Slack → ticket sync. It is
not active work; see "Deliberately deferred" below.

## Deliberately deferred

- Inbound Slack → ticket creation. Separate Slack-as-sync ticket.
- Multi-workspace Slack. One workspace assumed for now.
- Real-time sync (server backend). Git push/pull is the sync layer
  through ~5-person team size; revisit at 10+.
- `coga update-workflow` to re-snapshot a workflow into in-flight
  tickets. v1 is manual frontmatter edit.

## What this context does NOT cover

- Timeless principles — see `coga/principles`.
- The current iteration's *posture* (volatility, no real users) —
  see `coga/project-stage`.
- The mental model — see `coga/architecture`.
