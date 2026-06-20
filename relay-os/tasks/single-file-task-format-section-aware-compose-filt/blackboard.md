# Design notes — single-file task format

## STATUS: framed, NOT YET IMPLEMENTED (execution deferred — 2026-06-20)

This blackboard is the **frame** for the change, to be executed on a later day.
No code is written; nothing is on `main`. A trial implementation was attempted
this session and then **deliberately torn down** (worktree + branch
`single-file-task-format` removed at owner's request) — we want to plan/frame
now and code later. Everything below ("Implementation plan", "Progress",
"Owner re-confirmation") describes the *intended* implementation and the
verified code-surface map; treat it as the executable plan for the next
session, not as work already done. When picking this up: start fresh from this
plan (the ticket is still at the `implement` step).

## Decisions (design session, 2026-06-19, owner present)

1. **Log is global, not per-ticket.** One `relay-os/log.md` for the whole
   repo, `merge=union`, each line tagged with the task ref. This *overrides*
   the ticket's original "log stays inside the file, compose streams past it"
   framing. Rationale recorded in the ticket Description: it dissolves the
   stream/seek crux instead of solving it, and `merge=union` fixes per-task
   log merge conflicts.
2. **One global log per repo** (not per top-level dir).
3. **Single ticket / single PR, not siblings.** The cutover is atomic — format
   + every reader/writer change together or the repo is broken mid-migration.
   Atomicity, not size, is the reason. (Owner originally said "depends on
   size"; the size is large but the binding constraint is atomicity.)

## Format chosen

- Task file stays named `ticket.md` (discovery marker in `tasks.py:116`
  unchanged).
- Two regions after frontmatter, split by one fence `<!-- relay:blackboard -->`:
  body (above) + blackboard (below). No log region.
- Fail-loud: task ticket missing/duplicating the fence → error. Bootstrap
  shims (BootstrapRef) legitimately have no fence/blackboard.

## Code surface mapped (from exploration)

- Compose: only blackboard read at `compose.py:224-229`; sections via
  `_extract_section` (`208`, `235`); log never read. Clean to swap.
- `append_log`/`last_activity` live in `logfile.py` — single helper, easy to
  repoint at the global log. Status sorting uses `last_activity` per task
  (`status.py:131`) → needs a single-pass `last_activity_map` to avoid
  re-scanning the global log per task.
- Writers: create.py, bump, mark, panic, slack, launch, launch_script,
  project, git, notification/slack, recurring (`_record_run`), validate
  safe-fixes — all `append_log` callers.
- Blackboard readers/writers: blackboard.py (`append_to_section`,
  `append_blocker`, size warning), automerge.py (`## Dev` PR URL),
  period_state.py + recurring (`last_serviced_period`, state keys), show.py.
- No `.gitattributes` / merge=union exists yet — must add.

## Open Questions — RESOLVED (design session, owner present)

1. **Fence syntax** → `<!-- relay:blackboard -->` (HTML comment). RESOLVED.
2. **Global log path** → top-level `relay-os/log.md` (repo-scoped, not a
   task). My recommendation; no objection raised. RESOLVED (revisit at
   review-design if owner disagrees).
3. **Recurring template period-history** → fold into the global log tagged
   `recurring/<name>`; recurring template dirs collapse to one `ticket.md`.
   RESOLVED.
4. **`merge=union` duplicates** → accepted. Union merge may duplicate
   identical lines / not sort across branches; fine for an append-only audit
   log since readers sort on display. RESOLVED.
5. **Migration delivery** → throwaway one-shot script, run once on this repo
   then deleted (NOT a shipped subcommand). RESOLVED.

No open blockers remain for `review-design` — the questions above are recorded
as owner decisions, not unresolved choices.

## Design cleanup (2026-06-20, Codex)

- Verified the live code surface before handoff: `compose.py`, `logfile.py`,
  `blackboard.py`, `create.py`, `recurring.py`, `period_state.py`,
  `commands/show.py`, `commands/status.py`, and `validate.py` still assume
  sibling `blackboard.md` / `log.md` files.
- Tightened the ticket spec to name the actual broad design doc
  (`docs/design.md`, not `docs/spec.md`) and to make `read_task_file` take an
  explicit `blackboard_required` flag so bootstrap shims can remain fence-free
  without weakening fail-loud normal-task parsing.
- No unresolved product questions remain for `review-design`.

## Review-design (2026-06-20, Codex)

- Reviewed against `docs/vision.md`, `relay/principles`, `relay/current-direction`,
  `relay/project-stage`, and the live code surface. The one-ticket atomic cutover
  is the right shape for the current stage: no long-lived compatibility layer,
  no stream parser for unbounded per-task logs, and the composed prompt stays
  bounded and legible.
- Tightened one implementation detail before handoff: blackboard-only writers
  must splice the post-fence region and leave the pre-fence frontmatter/body
  bytes untouched, instead of re-rendering YAML via the parsed frontmatter.
- No remaining design blockers. Ready to hand off to `implement` once
  validation and the workflow transition succeed.

## Dev

(none — the trial worktree + branch `single-file-task-format` were torn down
on 2026-06-20 when execution was deferred. Start a fresh worktree next session.)

## Implementation plan (2026-06-20, Claude, implement step)

Core API in new module `src/relay/taskfile.py`:
- `BLACKBOARD_FENCE = "<!-- relay:blackboard -->"`
- `split_body(body, *, blackboard_required) -> (body_above, blackboard_below)` (fail-loud on 0/>1 fence when required)
- `read_task_file(path, *, blackboard_required=True) -> TaskFile(ticket, body, blackboard)`
- `read_blackboard(path, *, blackboard_required=True) -> str`
- `replace_blackboard(path, new_text)` — byte-splice post-fence region, frontmatter+body bytes above fence preserved verbatim (no YAML re-render)

Global log `relay-os/log.md` (= `cfg.repo_root / "log.md"`), line fmt
`YYYY-MM-DD HH:MM [<task-ref>] [<actor>] <msg>`; `.gitattributes` merge=union.
- `logfile.append_log(cfg, task_ref, actor, msg)` ; `last_activity_map(cfg) -> {ref: dt}` ; `last_activity(cfg, ref)`.

Writers reworked to region: blackboard.append_to_section/append_blocker/size_warning,
spool.append_record/read_records/drain, period_state, recurring last_serviced.
create.py writes one ticket.md (body + fence + blackboard template). Ticket model
stays body-opaque (status/step writes preserve the fence+blackboard region).

Readers: show (ticket.md + global-log history), status (last_activity_map),
validate (required = ticket.md only; fence-presence check; safe-fix), autoclose (## Dev in ticket.md region).

Migration: one-shot throwaway script (fold blackboard.md under fence, union all
log.md → global log tagged by ref, delete old files). Recurring templates too.

Docs+templates+fixture+tests in same PR.

## Implementation map (2026-06-20, Claude) — from the torn-down trial run

NOTE: the code below was written and verified-importing in a trial run, then
DISCARDED (worktree removed). Keep this as the precise edit map for the next
session — every item is a concrete edit that compiled, so it is the executable
recipe, but none of it currently exists on disk.

Edits that were made & import-verified (python3.12):
- NEW src/relay/taskfile.py — BLACKBOARD_FENCE, split_body, read_task_file,
  read_blackboard, replace_blackboard (byte-faithful pre-fence), join_task_body.
- paths.py: log_path(cfg)=relay-os/log.md.
- logfile.py: append_log(cfg, ref, actor, msg) → global log line
  `ts [ref] [actor] msg`; last_activity_map / last_activity / task_log_lines;
  ref_tag_for_path(cfg, path).
- compose.py: split body at fence; blackboard layer from region.
- blackboard.py: append_to_section/append_blocker/size_warning operate on
  ticket.md region.
- spool.py: region-aware (read_blackboard/replace_blackboard).
- create.py: writes ONE ticket.md (body+fence+blackboard); logs to global.
- period_state.py: reads parent template blackboard region from ticket.md.
- recurring.py (module): Template.ticket_path; read/write_last_serviced on
  region; _record_run → global log tagged recurring/<name> (threaded cfg).
- mark/bump/panic/slack/ticket/project/launch/launch_script: append_log → global;
  size-warning + RELAY_TASK_BLACKBOARD/LOG repointed; parent-blackboard → ticket.md.
- git.py: global log folded into LOCAL commit only, EXCLUDED from cross-branch
  overlay (would drop concurrent lines) — reaches control via merge=union.
  ref_tag_for_path used for sync-failure log.
- notification/__init__ + slack.py: digest spool path → ticket.md; failure log → global.
- autoclose.py: PR-URL scan reads ticket.md region.
- show.py: prints ticket.md + per-ref history from global log.
- status.py: last_activity_map (single pass).
- digest.py: digest-state read/write on region.
- validate.py: required file = ticket.md only; exactly-one-fence check
  (kind=blackboard-fence); size warning + idle on ticket.md; safe-fix adds fence+region.

KEY DESIGN DECISION (git): global log is union-merged and NEVER part of the
cross-branch control-landing overlay (overlay replaces a file wholesale → would
drop concurrently-appended log lines). It lands on control via the same-branch
push (rebase union-merges) or PR merge. High-water mark is NOT union-safe (single
mutable line, take-max) so it still needs explicit merge.

REMAINING:
1. commands/recurring.py — the big cross-branch merge machinery + _append_sync_failure
   (still old append_log sig). The log half DELETES (global+union); blackboard half
   adapts to ticket.md region (read_control high-water from ticket.md blob region;
   write merged high-water into working-tree ticket.md region). HIGH RISK — needs tests.
2. Templates: fold every recurring/task template blackboard.md into ticket.md under
   fence; delete blackboard.md/log.md; add relay-os/.gitattributes (log.md merge=union)
   + seed relay-os/log.md. Live (relay-os/) + packaged
   (src/relay/resources/templates/relay-os/). Verify Dream worker scripts' use of
   RELAY_TASK_BLACKBOARD (now ticket.md).
3. example/ fixture: fold the one task (auto/triage-inbound-email).
4. Migration: one-shot throwaway script (fold blackboards, union logs→global, delete).
5. Docs: architecture SKILL, codebase SKILL, base prompt (resources/prompt.md), cli
   context, README, docs/design.md, code/* skills, init.py docstrings, update.py
   vendored lists + .gitattributes shipping.
6. Tests: large update (test_*.py assuming 3 files) + new tests for fence/global-log/migration.

## Owner re-confirmation (2026-06-20, interactive)
Owner re-affirmed both calls when I surfaced the scope:
- ONE ticket / one PR (atomic cutover; no split, no dual-format layer).
- Global log = single `relay-os/log.md` + `merge=union` (not a directory).
Proceeding with the remaining work as planned.
