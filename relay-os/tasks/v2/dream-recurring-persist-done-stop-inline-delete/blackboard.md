The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design session (2026-06-08, interactive — spec only, no code yet)

Worked through the design with nick. This session refined the **ticket spec
only**; no `src/` edits, no bump. Two decisions that go beyond "just stop
deletion":

### Decision 1 — `--all` ignores done + schedule
`relay recurring --all` instantiates and launches **every** template's
current-period ticket, ignoring the schedule, the ledger "already ran" skip,
**and** `done` status. A `done` period is re-run by re-activating its on-disk
ticket via `relay launch` (relaunch restarts a `done` workflow at step 1). No
throwaway `-dbg-` scratch — the whole debug-run machinery is removed.

### Decision 2 — nothing blocks; queue all launchable by date
This is the bigger change. **Drop the current `one live task per template`
rule.** `scan_due` splits into two decoupled passes:
- **Create pass:** for each template, create the current-period ticket iff the
  ledger hasn't recorded that period; `_record_run`. Gated by the ledger ALONE.
- **Enqueue pass:** scan every `recurring-<name>-*` dir, enqueue all launchable
  (`active`/`in_progress`), sort by firing date (parsed from the slug's period
  key), run oldest-first. A template can appear twice (stuck old run + new
  period).

Crash handling becomes **resume-by-queue**: a crashed `in_progress` orphan is
still resumed from its `step:`, but it's queued by date, not given priority by
blocking/deferring. Decoupling create from enqueue is what lets the fresh
current-period ticket and a prior-period orphan coexist without one suppressing
the other.

`paused` = not deleted, not launchable, not blocking. Sits for a human.

### Decision 3 — no get-or-create; ledger is the only creation guard
nick: "there's no get or create — we just create even if there's a ticket
already (they shouldn't intersect from date, and might be in progress)." And on
the same-period edge he chose **"always create, never dedupe."**

Resolution: remove BOTH create-time dedup paths — `_task_with_slug`
(dir-existence) and `_live_task_for_template` (live-task superseding). The
**period ledger** becomes the single creation guard for the bare sweep: it
already prevents a same-period re-create (a second sweep in the same date
bucket is skipped because `_record_run` logged the first). So "never dedupe"
doesn't spam duplicates on the bare path — the ledger does.

`--all` ignores the ledger, so it genuinely always creates: if the period slug
dir already exists, the fresh create is **suffixed** (`…-<period>-2`) rather
than reusing/re-activating it. Duplicates for one period are accepted and all
launched. (This SUPERSEDES the earlier "--all re-activates the on-disk done
ticket" wording, which contradicted always-create.)

Implementation note: create needs a slug-collision strategy (suffix) so
always-create can't crash on an existing dir; and the enqueue pass needs a
helper to parse a firing date back out of a `recurring-<name>-<period>` slug.

### Confirmed from the start (already in spec / already true in code)
- Scan→create→execute-sequentially-by-date already exists (`scan_due` +
  `DueScan.due` + the sequential loop in `commands/recurring.py`).
- The crash bug is the **three deleters lying to the ledger**
  (`_finalize_debug_run`, `_reap_debug_orphans`, Dream self-`relay delete`):
  ledger writes `created` at creation, so a non-`done` dir deleted out from
  under it reads as "ran" → crashed period skipped forever. Removing the
  deleters is the fix.
- Dream is just another instantiated recurring ticket and is THE deleter
  (stage 3 = sibling ticket `dream-sweeps-done-recurring-period-tickets`). It
  does **not** self-delete mid-run; the *next* Dream run cleans up the previous
  one. Keep ledger — it's load-bearing for the deleted-after-`done` case.

### Consequence for context docs (in acceptance criteria)
`relay/recurring` must drop both the debug-reap/self-delete prose AND the
`one live task per template` / prior-period-supersedes prose, replacing the
latter with "nothing blocks; every launchable recurring ticket is queued and
run oldest-first." Keep live + packaged copies in sync.

### Note
Workflow step is `implement` but we are deliberately in design mode. Whoever
implements: read the refined Acceptance Criteria + Proposed Shape in ticket.md
first — they now encode Decisions 1 & 2.
