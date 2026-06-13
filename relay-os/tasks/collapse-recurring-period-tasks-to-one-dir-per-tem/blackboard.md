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

## Dev

- branch: codex/recurring-group-slugs
- worktree: /tmp/relay-recurring-group-slugs
- implementation note: clean-cut runtime change, no legacy
  `recurring-<name>-<period>` dual-shape support; update tracked context
  overrides and packaged bootstrap context sources together.
- migration decision: apply the tracked repo migration directly in this PR
  (delete old `tasks/recurring-<name>-<period>` dirs and seed template
  `last_serviced_period` lines) instead of adding a permanent scan-path guard
  or a new one-off scripts directory. This keeps the runtime clean-cut and
  avoids dead migration code after the current tracked state is fixed.
- implementation summary: recurring runtime now uses stable grouped task refs
  (`recurring/<name>`), group-based status/list filtering, and
  `last_serviced_period` in the template blackboard for dedup/control-branch
  sync. Debug runs remain top-level `*-dbg-*` scratch.
- commit: 1d3ef36 (`Collapse recurring runs to grouped task dirs`)
- pr: https://github.com/FastJVM/relay/pull/357 (no CI configured on repo;
  mergeable, no checks reported)
- tracked migration applied in worktree: removed old digest/dream period task
  dirs; seeded `relay-os/recurring/digest/blackboard.md` to `2026-06-11` and
  `relay-os/recurring/dream/blackboard.md` to `2026-W24`.
- verification:
  - `PYTHONPATH=/tmp/relay-recurring-group-slugs/src python -m pytest -q` →
    717 passed, 1 skipped.
  - `PYTHONPATH=/tmp/relay-recurring-group-slugs/src python -m relay.cli validate --task collapse-recurring-period-tasks-to-one-dir-per-tem --json` →
    ok_count 1, no issues.
  - repo-wide `relay validate --json` was attempted with an ignored local
    config copy and failed on pre-existing unrelated task/bootstrap issues
    (broken `bootstrap/ticket` refs, draft missing-workflow warnings, etc.),
    not on this task.

## Peer review (codex, step 2)

- `codex review --base main` found three must-fix P2s:
  - resuming an existing `active`/`in_progress` recurring task must not advance
    `last_serviced_period`; the stale run defers the new period until it is
    completed/deleted, otherwise the deferred period can be skipped.
  - stale-checkout handled-period races must preserve the control branch
    blackboard as the merge base and merge only the local high-water value.
  - packaged `relay/patterns` context had stale log-ledger wording and needed
    the same high-water wording as the live context.
- Applied fixes in `/tmp/relay-recurring-group-slugs`:
  - `src/relay/recurring.py`: live task return no longer calls
    `_advance_serviced_period`.
  - `src/relay/commands/recurring.py`: control blackboard text is now the
    merge base for `_control_blackboard_with_local_period`.
  - `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/patterns/SKILL.md`
    synced to the live context.
  - `tests/test_recurring.py` covers deferred-period high-water behavior and
    remote blackboard-state preservation in handled-period races.
- Verification after fixes:
  - `PYTHONPATH=/tmp/relay-recurring-group-slugs/src python -m pytest tests/test_recurring.py -q`
    → 68 passed.
  - `PYTHONPATH=/tmp/relay-recurring-group-slugs/src python -m pytest -q` →
    717 passed, 1 skipped.
  - Feature-worktree task validation could not run directly because
    `/tmp/relay-recurring-group-slugs/relay-os/relay.local.toml` has no `user`;
    I did not edit `relay.local.toml`.
  - `PYTHONPATH=/tmp/relay-recurring-group-slugs/src python -m relay.cli validate --task collapse-recurring-period-tasks-to-one-dir-per-tem --json`
    from the primary checkout → ok_count 1, no issues.
