# Design notes — single-file task format

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
