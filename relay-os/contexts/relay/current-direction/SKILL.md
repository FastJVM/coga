---
name: relay/current-direction
description: What we're building right now in relay. Recent decisions, open tickets, deferred features. Living document — updates every few weeks. Read this to avoid re-litigating closed decisions.
---

# Relay — current direction

Last updated: 2026-06-10.

## Open redesign (recurring lifecycle: generate → done → Dream-deletes)

- **Recurring period tickets get a single, ordinary task lifecycle — and the
  recurring command stops deleting anything.** Today the lifecycle is
  special-cased and self-contradicting: the bare sweep persists a period
  task, `relay recurring --all` scaffolds throwaway `<name>-dbg-<ts>` runs and
  `rmtree`s them, a crashed `--all` leaves orphans the *next* sweep reaps, and
  Dream `relay delete`s *itself* at the end of its own run. The three deleters
  (debug `_finalize_debug_run`, `_reap_debug_orphans`, Dream self-delete) are
  why a real run can look like it "started and got cleaned up," and they break
  the period ledger: `_record_run` writes `scaffolded <slug>` at *creation*,
  but a non-`done` dir getting deleted out from under it makes the ledger read
  "this period ran" when it only "was created" — so a crashed period is
  silently skipped forever.

  The target is the same three-stage lifecycle every other task already has,
  with one deleter:

  1. **Generate.** `relay recurring` scaffolds a normal task at
     `relay-os/tasks/recurring-<name>-<period>/`, status `active` → `in_progress`
     on launch. *(Already true — this is the only stage built today.)*
  2. **Done.** The run ends by marking its own ticket `done` (`relay mark done`,
     or `relay bump` past the final workflow step). The terminal on-disk state
     of a finished period is a **persistent `done` ticket**, never a deleted
     dir. The recurring command itself deletes *nothing*.
  3. **Delete (deferred to Dream/retro).** A `done` recurring period ticket is
     cleaned up by the same retro-first Dream pass that already deletes every
     other processed `done` ticket (see "Done-ticket cleanup is retro-first"
     below). Period tickets carry nothing durable — their output is the Slack
     post / PR — so they direct-delete. Each Dream run is itself a recurring
     period ticket, so it is cleaned up by the *next* Dream run, not by
     deleting itself mid-run.

  Why this fixes the never-runs bug: once the *only* thing that deletes a
  recurring ticket is Dream-acting-on-`done`, "ledger has the slug + dir gone"
  reliably means "this period completed." A crash leaves an `in_progress` dir
  Dream won't touch, so the next sweep **resumes** it; a parked run stays
  `paused` and is neither deleted nor wrongly skipped. The period ledger stays
  (it is load-bearing for the deleted-after-`done` case) — earlier notes that
  said "drop the ledger" were wrong under this model.

  `relay recurring --all` keeps its "ignore the schedule, exercise every
  template now" purpose but force-runs the **real** period tickets (persistent,
  active) instead of throwaway debug scratch — it loses the "isolated from real
  state" property by design. The debug throwaway machinery
  (`scaffold_debug_run`, `scan_debug`, `is_debug_slug`/`_DEBUG_SLUG_RE`,
  `_finalize_debug_run`, `_reap_debug_orphans`, `_read_debug_outcome`, and the
  `-dbg-` suppression in `git.py`/`slack.py`/`spool.py`) is all removed.

  Tickets implementing this: `dream-recurring-persist-done-stop-inline-delete`
  (stages 1–2: stop all inline deletion, `--all` force-runs real tickets, keep
  ledger, fix paused handling) and `dream-sweeps-done-recurring-period-tickets`
  (stage 3: Dream owns recurring-`*` `done` cleanup). **Stage 3 has landed:**
  the Dream template no longer self-deletes mid-run (its Phase 4 retro pass is
  now the single deleter of done `recurring-*` tickets, the previous Dream run
  included), and `relay/recurring` documents Dream-as-janitor under "Dream is
  the recurring janitor." Stages 1–2 are still open, so `relay/recurring` still
  documents the current `*-dbg-*` debug-reap behavior — don't edit that
  debug-reap prose ahead of the sibling's code.

## Open rename (workflow → playbook)

- **The `workflow` primitive is being renamed to `playbook`.** Ticket:
  `rename-workflow-primitive-to-playbook` (draft, `code/design-then-implement`).
  Same motive as the earlier `relay step → relay bump` rename below: the name
  mislabels the concept. "Workflow" imports the romantic, absorption-camp
  connotation (*the automation runs itself* — n8n/Zapier/CI), which is the
  opposite of what the primitive is: a sequence of **operator handoffs**
  (`assignee: agent | human | owner`) with a human gate in the step list. The
  product is literally a *relay* (baton between runners); "playbook" names the
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
  "Referenced-but-absent" skills are already fully covered: `relay validate`
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
  `relay validate` is enough. Decision closed the `detect-missing-skills`
  ticket (deleted without a build).

## Recent decisions (Dream — recurring template plus an alias)

- **Dream is a recurring task template plus an alias.** The standalone
  `relay dream` Typer command is gone. Dream now ships as
  `relay-os/recurring/dream/` — an ordinary recurring template. `relay
  recurring` scaffolds and launches it when its weekly schedule is due;
  `relay dream` is a default alias for `recurring launch dream`, which
  scaffolds and launches it on demand through the same path. The task slug is
  `recurring-<name>-<period>` (`recurring-dream-2026-W21`), so the two paths
  converge on one task. This reverses the earlier "ad-hoc command" decision: there was
  nothing left in a dedicated command worth keeping once the workers became
  skills.
- **`relay recurring launch <name>` is the on-demand recurring entry point.**
  It scaffolds one named template now, ignoring its schedule, with the same
  period-keyed (idempotent) slug a bare `relay recurring` produces, then
  launches the task.

## Recent decisions (Dream and REM)

- **Dream is Relay's generic ticket cleanup pass.** It scans all tickets, runs
  fixed Relay housekeeping skills, proposes done-ticket cleanup, keeps one
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
  the ticket is **direct-deleted** via `relay delete <slug>` (working-tree
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
  `agent_type_for(user, nickname)`. `relay.local.toml`'s
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
  held: `slack.py` now exposes
  `post(cfg, message, *, owner=..., watchers=...)` and a `_mention`
  helper that renders any name mapped in `[slack.users]` as a real
  `<@U…>` ping — owner inline, watchers cc'd in a trailer. Posts ping
  the ticket owner and watchers again; see `relay/sync` for the
  current behavior.

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
  current `step:` frontmatter and normally advances by one. Humans may
  rewind in-progress workflow tasks to an earlier step with `--to` or
  `--backward`; agents still panic instead of going backward. `bump` does
  not finish tickets — bumping past the last step (or on a no-workflow
  ticket) errors and points at `relay mark done`.
- **`relay recurring` is the canonical entry point** for the recurring
  scaffolder. It scans templates, scaffolds the current period's task for
  each, and launches the due ones sequentially — current period only, no
  backlog of missed periods. `scripts/cron.sh` calls it directly rather than
  going through `relay draft` / `scaffold_task()`.
- **Control plane and data plane are fully split.** `draft` is unapproved,
  `active` is approved/queued, and `in_progress` is launched work. `relay
  launch` owns the `active` → `in_progress` start transition; `relay bump`
  owns `step:` movement and only runs while the task is `in_progress`.
  The normal boot is `relay ticket "<title>"` → review the draft →
  `relay mark active <slug>` → `relay launch <slug>`.

## Open ticket queue (Slack / notifications)

The earlier audit-driven bug queue has been worked off — its tickets are
completed-and-pruned and no longer on disk. The live work now centers on
Slack/notifications. As of this refresh the on-disk tickets are:

- **`rename-slack-to-a-notification-system-with-pluggab`** (active) — the
  broader rename of Slack into a pluggable notification system. The other
  Slack tickets should stay narrow rather than fold into this one.
- Open Slack bug/feature drafts:
  `post-slack-notification-on-mode-script-failures`,
  `slack-post-ignores-http-response-so-bad-webhook-fa`,
  `slack-webhook-is-env-only-despite-toml-comment-imp`,
  `rewrite-slack-messages`, and `use-slack-as-a-sync-channel-for-tickets`.

This reflects the tickets present on disk at refresh time, not a committed
priority order — re-prioritize as needed.

## Deliberately deferred

- Inbound Slack → ticket creation. Separate Slack-as-sync ticket.
- Multi-workspace Slack. One workspace assumed for now.
- Real-time sync (server backend). Git push/pull is the sync layer
  through ~5-person team size; revisit at 10+.
- `relay update-workflow` to re-snapshot a workflow into in-flight
  tickets. v1 is manual frontmatter edit.

## What this context does NOT cover

- Timeless principles — see `relay/principles`.
- The current iteration's *posture* (volatility, no real users) —
  see `relay/project-stage`.
- The mental model — see `relay/architecture`.
