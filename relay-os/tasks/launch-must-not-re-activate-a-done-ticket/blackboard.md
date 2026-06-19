## Dev

branch: launch-done-guard
worktree: ../relay-launch-done-guard

## Plan

`relay launch` on a `done` ticket auto-activates it (re-seeds `step: 1`
without re-resolving `assignee`), then crashes on the `agent_type(<human>)`
lookup and leaves the ticket wedged (`active, step 1, assignee=<human>`).

Fix: refuse to launch a `done` ticket *before* `_auto_activate` runs, so it is
never restarted. Surface = fail loud + hint (human decision), pointing at
`relay mark active <slug>` to reopen. Draft/paused still activate inline.

Done case never reaches `_auto_activate` now, so the separate
assignee-not-re-resolved-on-reseed gap is unreachable via launch (reopening is
the deliberate `mark active` path).

## Changes

- `commands/launch.py`: explicit `done` bail before the auto-activate block;
  updated the `_auto_activate` docstring/comment (it no longer sees `done`).
- `tests/test_launch.py`: replaced `test_launch_auto_activates_done_and_reseeds_step`
  (asserted the old buggy restart) with `test_launch_refuses_done_ticket`,
  asserting the refusal leaves the ticket `done` and unmodified, no agent spawned.

## Verification

- `tests/test_launch.py`: 66 passed (incl. new refusal test).
- Full suite: 806 passed, 1 skipped, 2 failed.
- The 2 failures are in `tests/test_autoclose_sweep.py`
  (`..._creates_idempotently`, `..._live_and_packaged_copies_stay_in_sync`).
  **Pre-existing, unrelated to this change** — confirmed they fail identically
  on the unmodified primary checkout. They are date-sensitive
  (`last_serviced_period` computes 2026-06-17 vs expected 2026-06-11 given
  today 2026-06-18) and one is entangled with the already-uncommitted
  `relay-os/recurring/digest/blackboard.md` edit. Not masking; not mine to fix.

Ran with: `PYTHONPATH=$PWD/src python3.12 -m pytest` (3.9 conda python lacks
tomllib; .relay/.venv absent on this machine).
