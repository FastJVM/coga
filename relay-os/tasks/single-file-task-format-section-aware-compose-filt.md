---
slug: single-file-task-format-section-aware-compose-filt
title: Single-file task format + section-aware compose filter
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Collapse the three-file-per-task layout (`ticket.md` + `blackboard.md` +
`log.md`) into **one file per task** (`ticket.md` = frontmatter + body +
blackboard) and move the append-only audit trail out of the task directory
entirely into **one global, union-merged log** (`relay-os/log.md`). A
**section-aware compose reader** then loads only frontmatter + body +
blackboard and never touches the log.

### Revised owner decision (supersedes the original framing)

The ticket originally recorded the log staying *inside* the per-task file as
an unbounded section that compose would stream/seek past. In design (interactive
session, 2026-06-19) the owner **reversed** that: the log is no longer
per-ticket at all. It becomes a single repo-level `relay-os/log.md`, each line
tagged with its task ref, with `merge=union` git semantics so concurrent
appends across branches merge cleanly.

This is strictly more legible and it *dissolves the original crux* rather than
solving it:

- The per-task file is now always small and bounded (frontmatter + body +
  blackboard), so compose goes back to the "dumbest legible version" — read the
  small task file, ignore the log. **No stream/seek-past-an-unbounded-section
  parser is needed**, because the unbounded thing is no longer in the file
  compose opens.
- The section reader still exists (it splits body from blackboard so each lands
  in the right prompt layer) but only ever parses a small bounded file, so the
  fail-loud requirement is cheap to honor.
- The unbounded growth now lives in one file compose never reads, and
  `merge=union` fixes the per-task-log merge-conflict problem the old layout
  had.

### Scope

1. **Format** — one `ticket.md` per task: YAML frontmatter, the body sections
   (`## Description`, `## Context`, plus spec sections), then a single
   machine-findable fence `<!-- relay:blackboard -->` followed by the freeform
   blackboard region. Exactly two regions after frontmatter (body above the
   fence, blackboard below); the log is *not* a region.
2. **Global log** — `relay-os/log.md`, append-only, one per repo. Each line
   `YYYY-MM-DD HH:MM [<task-ref>] [<actor>] <message>` so per-task history is
   reconstructable by filtering on the ref. `.gitattributes` marks it
   `merge=union` (live repo + packaged template).
3. **Compose reader** — a `read_task_file()` helper splits frontmatter / body /
   blackboard; compose feeds Description→task-description layer,
   Context→inline-context layer, blackboard→blackboard layer. Fail-loud on a
   task ticket missing the fence; never silently fold blackboard into body or
   vice versa.
4. **Writers** — every `append_log` caller moves to the global log; every
   blackboard writer (`append_to_section`, `append_blocker`, recurring
   `last_serviced_period`, size-warning) operates on the blackboard region of
   the one file. Scaffolding (`create.py`) writes one file, not three.
5. **Reads / surfaces** — `relay show` (per-task history from the global log),
   `status` (`last_activity` from the global log), `validate`, `automerge`
   (PR-URL scan), `period_state` (recurring state-keys) read the new format.
6. **Migration** — one-shot, idempotent, fail-loud: fold each task's
   `blackboard.md` into its `ticket.md` under the fence; union all `log.md`
   lines (task + recurring template) into `relay-os/log.md` sorted by
   timestamp and tagged by ref; delete the old `blackboard.md` / `log.md`.
   Bootstrap shims (`ticket.md` only, no blackboard, no log) are left as-is.
7. **Docs** — rewrite every place that teaches the three-file model:
   `relay/architecture`, the base prompt, `relay/cli`, README, `docs/design.md`,
   and the `code/*` skills that name `blackboard.md`/`log.md`. Ship in the same
   PR as the behavior change. In this checkout the broad design doc is
   `docs/design.md` (there is no `docs/spec.md`); update any generated/live
   `relay/cli` context copy that exists.

### Shape decision: one ticket, not siblings

The ticket speculated this might split into sibling tickets (format+migration /
compose / writers / docs). **It does not.** The cutover is atomic: the on-disk
format and *every* reader and writer that touches it (~12 modules) must change
together, or the repo is broken between commits — there is no intermediate
state where half the tasks are migrated and both the old and new readers work.
The alternative (an expand→migrate→contract dual-format compatibility layer)
buys reviewable increments at the cost of throwaway dual-format code, and is not
worth it for a one-shot migration inside a single repo with no external
consumers of the on-disk format. So: one ticket, one PR, docs included (the
ticket already requires behavior + docs in the same PR). See
`## Open Questions` on the blackboard for the owner to confirm this call.

## Acceptance Criteria

- [ ] A task's canonical mutable state is in its `ticket.md` only; no
  `blackboard.md` or `log.md` exists under `tasks/` or `recurring/` after
  migration. Existing auxiliary dotfiles such as `.state-snapshot.json` keep
  their current meaning.
- [ ] `ticket.md` for a task has: frontmatter, a body region, a single
  `<!-- relay:blackboard -->` fence, and a blackboard region. A bootstrap shim
  has frontmatter + body and no fence.
- [ ] `relay-os/log.md` exists, is append-only, and every line carries
  `YYYY-MM-DD HH:MM [<task-ref>] [<actor>] <message>`. `.gitattributes` marks
  it `merge=union` in both the live repo and the packaged template tree.
- [ ] `read_task_file()` returns `(frontmatter, body, blackboard)` and raises a
  clear error on a task ticket with no/duplicate fence — it never silently
  drops or merges a region. Covered by a unit test for the malformed case.
- [ ] Composed prompt is byte-identical in content to the pre-change prompt for
  a representative migrated task (same Description, Context, blackboard layers;
  log absent as before). A compose test asserts the log never appears.
- [ ] Every former `append_log` call site writes a correctly-tagged line to the
  global log; `relay show <task>` reconstructs that task's history from it;
  `relay status` ordering by last activity is unchanged.
- [ ] Recurring `last_serviced_period` / state-keys and `automerge`'s
  `## Dev` PR-URL scan read from the blackboard region of the one file.
- [ ] Blackboard-only writes splice the post-fence region and leave the
  frontmatter/body region byte-for-byte unchanged; commands that intentionally
  mutate frontmatter keep using the existing ticket writer path.
- [ ] The one-shot migration is idempotent (re-running is a no-op) and
  fail-loud (a dir it can't safely fold errors instead of guessing); the
  seeded `example/` repo and `_template` are migrated.
- [ ] Docs in `relay/architecture`, base prompt, `relay/cli`, README,
  `docs/design.md`, and affected `code/*` skills no longer describe a
  per-task `log.md` / three-file model.
- [ ] `python -m pytest` and `relay validate --json` pass.

## Proposed Shape

**New module `src/relay/task_file.py`** (the single legible seam):
- `BLACKBOARD_FENCE = "<!-- relay:blackboard -->"`.
- `read_task_file(path, *, blackboard_required: bool) -> TaskFile(frontmatter:
  dict, body: str, blackboard: str | None)` — reuse `Ticket.parse` for the
  frontmatter/body split, then split the body on the fence. Exactly zero fences
  is allowed only when the caller says `blackboard_required=False` (bootstrap
  shims); zero fences for normal tasks or recurring templates is an error; one
  fence → `(body, blackboard)`; more than one → error.
- `write_task_file(path, task_file)` or narrower helpers preserve the exact
  pre-fence text when rewriting only the blackboard region. Do not use parsed
  frontmatter as an excuse to re-render YAML during a blackboard append; the
  frontmatter-mutating commands can keep their current `Ticket.write` path.
  Blackboard-region writers (`append_to_section`, `append_blocker`, recurring
  state updates) rewrite only the post-fence region.

**Global log — rewrite `src/relay/logfile.py`:**
- `append_log(cfg, task_ref, actor, message)` → appends
  `… [<task_ref.id_slug>] [<actor>] <message>` to `relay-os/log.md` in
  `O_APPEND` mode. Resolve the global-log path via a `paths.py` helper.
- `last_activity(cfg, task_ref)` and a single-pass `last_activity_map(cfg)`
  (one scan of the global log → `{ref: datetime}`) for `status.py`, so status
  doesn't re-read the whole log per task.
- `history_for(cfg, task_ref) -> list[str]` for `relay show`.

**Compose — `src/relay/compose.py`:** replace the `blackboard.md` read
(`224-229`) and the two `_extract_section` calls (`208`, `235`) with
`read_task_file()`; map body→Description/Context, blackboard→layer 7. Net
simplification.

**Writers (mechanical, once the helpers exist):** `create.py` (scaffold one
file + fence; first global-log line), `bump.py`, `mark.py`, `panic.py`,
`slack.py`, `launch.py`, `launch_script.py`, `project.py`, `git.py`,
`notification/slack.py`, `recurring.py` (`_record_run` → global log;
template `last_serviced_period`/state in the blackboard region),
`validate.py` (safe-fixes + idle detection from global log),
`blackboard.py` (region-scoped), `automerge.py`, `period_state.py`,
`commands/show.py` (history from global log), `commands/status.py`
(`last_activity_map`).

**Migration — throwaway one-shot script (NOT a shipped `relay` subcommand;
owner decision — run once on this repo, then delete):** for each
`tasks/**/ticket.md` and
`recurring/*/ticket.md`: append `\n<fence>\n` + `blackboard.md` body to
`ticket.md`; collect `log.md` lines, re-tag with the ref. Union all collected
lines across all tasks, sort by the `YYYY-MM-DD HH:MM` prefix (stable on ties),
write `relay-os/log.md`. Delete the old `blackboard.md`/`log.md`. Skip
bootstrap shims. Idempotent: detect an already-migrated file (fence present /
no `blackboard.md`) and no-op. Migrate `example/` and `_template` too.

**`.gitattributes`:** add `relay-os/log.md merge=union` to the live repo and
`src/relay/resources/templates/relay-os/.gitattributes`.

## Out of Scope

- Changing the canonical frontmatter schema or any field semantics
  (`status`/`step` stay CLI-owned; hand-edits to frontmatter/body stay safe).
- Per-team or per-subtree logs — decided: exactly one `relay-os/log.md` per
  repo.
- Changing blackboard freeform semantics (agents still invent headings inside
  the blackboard region).
- A general dual-format / backward-compat reader — the migration is a single
  atomic cutover, not a long-lived compatibility window.
- Re-enabling `mode: auto`, recurring scheduling changes, or any behavior not
  required by the format change.
- A `relay log` query UI beyond what `relay show` already renders.

## Context

This reverses a deliberate part of the current architecture, so read
`relay/architecture` (the three-file model, the two state planes, and the
prompt-composition layer list — note that `log.md` is explicitly *never* a
composition layer) before designing. The single-file format must preserve every
invariant that split bought: the working section stays small and is composed;
the audit section can grow unbounded and is never composed; status/step remain
CLI-owned; hand-edits to frontmatter and body stay safe.

Source layout and test expectations are in `relay/codebase`. Keep the live
`relay-os/` copy and the packaged `src/relay/resources/templates/relay-os/`
copy of any touched contexts/templates in sync (see CLAUDE.md).

<!-- relay:blackboard -->

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
