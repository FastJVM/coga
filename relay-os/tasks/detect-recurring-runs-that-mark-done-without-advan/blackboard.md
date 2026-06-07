# Detect recurring runs that mark done without advancing declared state

## Dev
branch: detect-stale-recurring-state
worktree: ../relay-state-advance

## Findings (codebase map)

- **Period task → parent link**: period slug is `<parent>-<period_key>`; the
  `relay/period-task` context (auto-attached at scaffold) tells the run to
  read/write `relay-os/recurring/<parent>/blackboard.md`. No explicit
  backpointer field — but at scaffold time we *know* the parent (`template.name`).
- **Parent blackboard** is freeform markdown; state is `key: value` lines under a
  section (e.g. `### Dev Update State` → `last_commit: <SHA>`). No structured key
  parser exists in core today.
- **Lifecycle finalizers** live in `src/relay/mark.py` (`mark_done`,
  `mark_in_progress`) and `src/relay/bump.py` (`advance_step`). Each has
  `cfg, ref, ticket` in hand; writes ticket, logs, `notify(...)`, git-syncs.
- **Scaffold** of a period task: `recurring.py::_scaffold_at_slug` — has the
  `Template` (frontmatter + blackboard_path) at hand. Ideal place to snapshot a
  baseline.
- **Debug runs** (`-dbg-<stamp>`) also go through `_scaffold_at_slug`; broadcasts
  are suppressed for them via `is_debug_slug`.
- **validate.py** does NOT currently look at recurring at all. Report/Issue shape:
  `Issue(kind, task, message, severity)`; JSON via `--json`.
- Recurring frontmatter is only loosely validated (`Template.load` requires just
  `schedule`) — adding a new `state_keys` field is safe.
- Packaged recurring templates (`src/relay/resources/templates/relay-os/recurring/`)
  are only `dream`, `_rem`, `_template`. `relay-dev-update` is repo-local only.

## Proposed design (the spine)

1. **Machine-readable contract**: recurring `ticket.md` frontmatter declares the
   keys it owns, e.g. `state_keys: [last_commit]`.
2. **Baseline snapshot at scaffold**: `_scaffold_at_slug` reads the parent
   blackboard's declared keys and writes a small artifact into the period task
   dir (`.state-snapshot.json`: parent name + `{key: value}` at scaffold). Only
   tasks with declared keys get one → the whole check keys off this artifact's
   presence, so non-recurring tasks are untouched.
3. **Compare at finish**: in `mark_done` (and final `bump`/`advance_step`), if a
   `.state-snapshot.json` is present, re-read the parent blackboard's current key
   values and diff against the snapshot. Any unchanged declared key → flag.
4. **Surface**: local warn echo + FYI broadcast (suppressed for debug slugs).
5. **validate (optional)**: reuse the comparison against still-present period
   tasks' snapshots so a stuck cursor is visible without waiting for next firing.

### Decisions (locked with human, 2026-06-07)
- **Contract**: `state_keys: [...]` list in recurring `ticket.md` frontmatter.
- **Severity**: warn + FYI broadcast; never hard-block `mark done`.
- **Skip case**: always warn on an unchanged key (no skip-sentinel logic).
  Genuine no-work periods produce a harmless false-positive warning — accepted.
- **Validate**: include the static stuck-cursor check now.

### Why NOT in `relay bump`
`advance_step` only moves *to* a step (1..N); completion is always `mark done`.
Intermediate steps legitimately haven't advanced state yet, so warning on bump
would be wrong. The check lives only at `mark_done` + `validate`.

## Final implementation plan
1. NEW `src/relay/period_state.py` — pure detection: `parse_keys`,
   `write_snapshot`, `read_snapshot`, `stale_keys`. Snapshot artifact is
   `.state-snapshot.json` in the period task dir: `{parent, keys:{k:v}}`.
   Whole mechanism keys off this file's presence → non-recurring tasks untouched.
2. `recurring.py::_scaffold_at_slug` — when the template declares `state_keys`,
   snapshot the parent blackboard's current values into the new period task dir.
3. `mark.py::mark_done` — after git sync, if a snapshot exists and any declared
   key is unchanged: local warn echo + FYI `post` (suppressed for `-dbg-` runs).
   Best-effort: broadcast wrapped so it never breaks a successful completion.
4. `validate.py::_check_one_task` — for a `done` task with a snapshot whose keys
   are unchanged vs the live parent blackboard, emit
   `Issue(kind="recurring-state-stuck", severity="warn")`.
5. `relay-os/recurring/relay-dev-update/ticket.md` — declare `state_keys:
   [last_commit]`. Keep packaged/live copies + period-task context in sync.
6. Tests: unit `tests/test_period_state.py` + integration touchpoints.

## Implementation result (2026-06-07)
Done on branch `detect-stale-recurring-state`. Files:
- NEW `src/relay/period_state.py` — pure detection (snapshot + key diff).
- `recurring.py::_scaffold_at_slug` — writes `.state-snapshot.json` when the
  template declares `state_keys`.
- `mark.py::mark_done` — `_warn_if_state_not_advanced`: local warn + FYI
  broadcast (debug-suppressed, best-effort so it never breaks completion).
- `validate.py` — new `recurring-state-stuck` warn Issue on done tasks.
- `relay-os/recurring/relay-dev-update/ticket.md` — declares
  `state_keys: [last_commit]`.
- period-task context + `_template` recurring ticket document the field
  (live + packaged copies kept in sync).
- `tests/test_period_state.py` — 15 tests (pure helpers, scaffold snapshot,
  mark-done warn/quiet, validate flag/quiet). All pass.

Full suite: **592 passed, 1 skipped, 0 failed** (fully green).
- The pre-existing unrelated failure
  (`test_cleanup_orphan_markers_declares_contract`) was fixed at the human's
  request in a separate commit: the cleanup-orphan-markers SKILL.md wrapped the
  phrase "reports eligible candidates as `human-needed`" across a newline, so
  the literal-substring assertion failed. Reflowed the prose to keep the phrase
  on one physical line (prose-only, semantically identical), matching the
  single-line-substring convention every sibling assertion uses.

Note: tests in a worktree run via
`PYTHONPATH=<wt>/src /home/n/Code/relay/.venv/bin/python -m pytest`
(editable install points at the primary checkout).

### Design notes / edge cases handled
- Mechanism keys off snapshot presence → non-recurring tasks fully untouched.
- Deleted/renamed parent → blackboard reads empty → declared values (non-None)
  no longer match → no false warning.
- Debug runs still snapshot + warn locally but never broadcast.
- Corrupt snapshot → treated as absent (advisory must never crash a finish).
