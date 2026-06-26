---
slug: v2/dream-recurring-persist-done-stop-inline-delete
title: Recurring runs persist as done; stop inline deletion
status: paused
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/recurring
- relay/architecture
- relay/current-direction
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Stages 1–2 of the recurring-lifecycle redesign in `relay/current-direction`
("Open redesign (recurring lifecycle: generate → done → Dream-deletes)").

Make a finished recurring run's terminal on-disk state a **persistent `done`
ticket**, and make `relay recurring` delete *nothing*. Today three deleters
contradict that — debug `_finalize_debug_run`, `_reap_debug_orphans`, and
Dream's self-`relay delete` — and they break the period ledger (it records
`created` at creation, so a non-`done` dir deleted out from under it makes a
crashed period look "already ran" and get skipped forever). Removing inline
deletion is what lets the ledger's "slug recorded + dir gone" reliably mean
"this period completed" (stage-3 deletion moves to Dream in the sibling ticket
`dream-sweeps-done-recurring-period-tickets`).

Stage 3 (Dream deleting `done` recurring-`*` tickets) is **out of scope here** —
it is the sibling ticket. This ticket only *stops* the inline/self deletion and
leaves finished runs sitting as `done`.

## Acceptance Criteria

- `relay recurring` (bare and `--all`) never deletes a task directory. After a
  finished run, the period ticket remains on disk as `status: done`.
- **No get-or-create — creation is gated solely by the period ledger.** Bare
  `relay recurring` **creates** the current-period ticket for every template
  whose current period the ledger has not already recorded. It no longer dedupes
  against an existing dir (`_task_with_slug`) or reuses/supersedes a live
  prior-period task (`_live_task_for_template`). A second sweep in the same date
  bucket is suppressed by the **ledger skip**, not by reusing a dir — the ledger
  is the single source of "did this period run." This **drops the current
  `one live task per template` rule** and the dir-existence idempotency.
- **Crash handling is resume-by-queue, not block.** Enqueue is a separate pass
  from creation: scan every `recurring-<name>-*` task dir and enqueue every
  launchable one — `active` plus `in_progress` orphans (a dead sweep's frozen
  run) — ordered by firing date (derived from the slug's period key), oldest
  first, executed sequentially. A crashed `in_progress` orphan is still
  **resumed** from its `step:`; it is queued by date alongside the fresh
  current-period task, not given priority by blocking. A template can contribute
  more than one ticket to a sweep (a stuck old run + the new period). Decoupling
  create from enqueue is what lets both coexist without one suppressing the other.
- `relay recurring --all` ignores schedule, ledger, **and** `done` status
  entirely and **creates a fresh** current-period ticket for every template —
  never reusing or re-activating an existing dir. If the period slug already
  exists on disk, the fresh create is suffixed (`...-<period>-2`); duplicate
  tickets for one period are accepted and all are launched. No throwaway
  `-dbg-` scratch, no `rmtree`.
- Dream's run no longer ends with `relay delete <self>` (both
  `relay-os/recurring/dream/ticket.md` and the packaged copy under
  `src/relay/resources/templates/...`).
- The period ledger (`_record_run` / `_period_already_created`) is **kept**
  and becomes the *only* creation guard for the bare sweep: it suppresses a
  same-period re-create and skips a period whose `done` ticket Dream later
  deletes. `--all` ignores it.
- A `paused` recurring run is neither deleted, re-run, nor blocking: it is left
  on disk for a human, is not launchable, and does not stop the next period
  from creating or launching.
- The debug throwaway machinery is removed and its tests updated, not just
  skipped: `create_debug_run`, `scan_debug`, `is_debug_slug`/`_DEBUG_SLUG_RE`,
  `_finalize_debug_run`, `_reap_debug_orphans`, `_read_debug_outcome`, and the
  `-dbg-` suppression branches in `git.py`, `slack.py`, `spool.py`.
- `relay/recurring` context updated to the new lifecycle: drop the debug-reap /
  self-delete prose **and** the `one live task per template` / prior-period
  superseding prose, replacing it with "nothing blocks; every launchable
  recurring ticket is queued and run oldest-first." Also restate the
  idempotency rule: the bare sweep is idempotent **via the period ledger** (not
  dir-convergence), and `--all` is intentionally non-idempotent (creates fresh,
  suffixes on collision). `relay/current-direction` redesign block trimmed to
  reflect what shipped. Live + packaged copies kept in sync.
- `python -m pytest` and `relay validate --json` pass.

## Proposed Shape

- `src/relay/recurring.py` —
  - Delete `create_debug_run`, `scan_debug`, `is_debug_slug`,
    `_DEBUG_SLUG_RE`. Keep `_record_run` / `_period_already_created`.
  - Split `scan_due` into two decoupled passes:
    - **Create pass:** for every template, if `_period_already_created`
      (ledger) is False for the current period, create it and `_record_run`.
      No `_task_with_slug` dedup, no `_live_task_for_template` short-circuit —
      the ledger is the sole creation guard.
    - **Enqueue pass:** scan every `recurring-<name>-*` task dir; enqueue each
      `active`/`in_progress` one with a firing date derived from its slug's
      period key; sort oldest-first. A template may appear more than once.
  - Delete `_live_task_for_template` (its superseding role is gone) and the
    `_task_with_slug` create-time dedup. Add a small helper to parse a firing
    date back out of a `recurring-<name>-<period_key>` slug for ordering.
  - `create_template` always creates the current period; it never returns an
    existing live task. Decide slug-collision behavior for the `--all` /
    ledger-bypass path (suffix `…-<period>-N`) so "never dedupe" can't crash on
    an existing dir.
- `src/relay/commands/recurring.py` —
  - Delete `_finalize_debug_run`, `_reap_debug_orphans`, `_read_debug_outcome`
    and the reap call at sweep start.
  - Rewrite `_launch_all_debug` (→ a non-debug `--all` path) so `--all`
    creates a fresh current-period ticket for every template ignoring schedule,
    ledger, **and** `done` status (suffixing the slug on collision rather than
    reusing the existing dir), then launches them date-ordered.
  - Keep `_stop_if_unfinished_after_launch` pausing an unfinished interactive
    run; confirm a `paused` ticket is not launchable (so it isn't re-launched
    next sweep) and is never read back as `done`.
- `src/relay/git.py`, `slack.py`, `spool.py` — remove the now-dead `-dbg-`
  predicates.
- `relay-os/recurring/dream/ticket.md` (+ packaged copy) — drop the final
  `relay delete <this-dream-task>` step and reword the "disposable" rationale.
- Tests: `tests/test_recurring.py`, `tests/test_git.py`, `tests/test_digest.py`
  — cover: ledger-gated create (second same-period sweep creates nothing);
  no-blocking queue (prior-period orphan + fresh current period both enqueued,
  date-ordered); `--all` creating a fresh suffixed ticket over an existing
  `done` period and launching it.

## Out of Scope

- Stage 3: Dream sweeping `done` recurring-`*` tickets — sibling ticket
  `dream-sweeps-done-recurring-period-tickets`.
- Grouping period tickets under a `tasks/recurring/` subdirectory — the flat
  `recurring-` prefix stays; a real subdir is a separate, larger refactor of
  `list_tasks`/slug resolution.

## Context

See `relay/current-direction` → "Open redesign (recurring lifecycle)" for the
full rationale and the never-runs bug this closes. `relay/recurring` documents
the current (to-be-replaced) create/ledger/debug behavior.

<!-- relay:blackboard -->

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
