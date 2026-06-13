# Blackboard — collapse recurring period tasks

## Design decisions (locked with nick, design step)

- **Two dirs, not one.** `recurring/<name>/` stays the persistent
  template/control + state home; `tasks/recurring/<name>/` is the instantiated
  run (stable group slug, no period). Not merged.
- **Period lives in the recurring-dir blackboard** as a single
  `last_serviced_period` high-water mark (overwritten, not a growing list — a
  list would bloat the prompt-composed blackboard; the unbounded period
  history stays in `log.md`).
- **Instantiated task is deleted at end of run** (unchanged). So there is no
  per-period blackboard reset to design, and a *leftover* `tasks/recurring/
  <name>/` dir is itself the orphan signal.
- **Dedup** = `last_serviced >= computed period_key`. Works after the run dir
  is gone.
- **Orphan resume** = leftover dir with recorded period ≠ current period_key →
  resume, then advance high-water. Prefer `in_progress` over `active`.
- **Status identity** derives from `group == "recurring"`, not the
  `recurring-` prefix.
- **Debug runs** stay top-level (`tasks/<name>-dbg-<ts>`), outside the group,
  excluded from resume/dedup.
- **Migration = clean-cut.** Delete old per-period dirs; seed each high-water
  mark from the newest `scaffolded …` line in `log.md`. No dual-shape support.

## Open Questions

- **The ticket's `is_recurring_period_task` and `_reap_debug_orphans` symbols
  do not exist in the tree.** Real symbols: `is_recurring_slug`
  (recurring.py:360) for status peeling, and the `_DEBUG_SLUG_RE` /
  `is_debug_slug` (:350-353) reaper logic. The implement step should treat the
  Proposed Shape's real symbol names as authoritative, not the ticket's
  Description prose. Flagging so review-design doesn't trip on the mismatch.
- **Migration mechanism (step 8): throwaway script vs guarded one-shot in
  `scan_due`?** Leaning throwaway script committed in the PR + a note, since a
  permanent guard in the hot scan path is dead weight after one run. Owner can
  weigh in at review-design.

## Notes / investigation

- `scaffold_task` (scaffold.py:112-124) always does `tasks_dir(cfg) / slug` +
  `mkdir(parents=True)`, so a slashed `slug_override="recurring/<name>"` should
  land the group dir for free — but the uniqueness check (`scaffold.py:115`)
  only inspects top-level leaves; verify no surprise when the leaf name
  collides with a top-level task.
- `relay/period-task` context currently points cross-run state at the parent
  recurring blackboard already — so the rewrite is mostly s/parse-your-slug/
  read-the-high-water-line/, not a conceptual change.
