---
title: Recurring runs persist as done; stop inline deletion
status: in_progress
mode: interactive
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
`scaffolded` at creation, so a non-`done` dir deleted out from under it makes a
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
- `relay recurring --all` force-runs the **real** `recurring-<name>-<period>`
  tickets (persistent, active) — no throwaway `-dbg-` scratch, no `rmtree`.
- Dream's run no longer ends with `relay delete <self>` (both
  `relay-os/recurring/dream/ticket.md` and the packaged copy under
  `src/relay/resources/templates/...`).
- The period ledger (`_record_run` / `_period_already_scaffolded`) is **kept**
  and still skips a period whose `done` ticket Dream later deletes.
- A `paused` recurring run is neither deleted nor wrongly treated as `done`:
  it is left for a human and does not block the next period's scaffold.
- The debug throwaway machinery is removed and its tests updated, not just
  skipped: `scaffold_debug_run`, `scan_debug`, `is_debug_slug`/`_DEBUG_SLUG_RE`,
  `_finalize_debug_run`, `_reap_debug_orphans`, `_read_debug_outcome`, and the
  `-dbg-` suppression branches in `git.py`, `slack.py`, `spool.py`.
- `relay/recurring` context updated to the new lifecycle (drop the debug-reap /
  self-delete / "pause unfinished" prose); `relay/current-direction` redesign
  block trimmed to reflect what shipped. Live + packaged copies kept in sync.
- `python -m pytest` and `relay validate --json` pass.

## Proposed Shape

- `src/relay/recurring.py` — delete `scaffold_debug_run`, `scan_debug`,
  `is_debug_slug`, `_DEBUG_SLUG_RE`. Keep `_record_run` /
  `_period_already_scaffolded`. In `scan_due`/`scaffold_template`, add explicit
  `paused` handling (leave it; don't let a prior-period paused orphan block the
  current period).
- `src/relay/commands/recurring.py` — delete `_finalize_debug_run`,
  `_reap_debug_orphans`, `_read_debug_outcome` and the reap call; rewrite
  `_launch_all_debug` so `--all` get-or-creates and launches the real period
  tickets. Revisit `_stop_if_unfinished_after_launch` (pausing an unfinished
  interactive run is fine; just ensure paused isn't later read as done).
- `src/relay/git.py`, `slack.py`, `spool.py` — remove the now-dead `-dbg-`
  predicates.
- `relay-os/recurring/dream/ticket.md` (+ packaged copy) — drop the final
  `relay delete <this-dream-task>` step and reword the "disposable" rationale.
- Tests: `tests/test_recurring.py`, `tests/test_git.py`, `tests/test_digest.py`.

## Out of Scope

- Stage 3: Dream sweeping `done` recurring-`*` tickets — sibling ticket
  `dream-sweeps-done-recurring-period-tickets`.
- Grouping period tickets under a `tasks/recurring/` subdirectory — the flat
  `recurring-` prefix stays; a real subdir is a separate, larger refactor of
  `list_tasks`/slug resolution.

## Context

See `relay/current-direction` → "Open redesign (recurring lifecycle)" for the
full rationale and the never-runs bug this closes. `relay/recurring` documents
the current (to-be-replaced) scaffold/ledger/debug behavior.
