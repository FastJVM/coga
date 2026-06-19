## Dev

branch: launch-done-guard
worktree: ../relay-launch-done-guard
pr: https://github.com/FastJVM/relay/pull/403

## Plan

`relay launch` on a `done` ticket auto-activates it (re-seeds `step: 1`
without re-resolving `assignee`), then crashes on the `agent_type(<human>)`
lookup and leaves the ticket wedged (`active, step 1, assignee=<human>`).

Fix: refuse to launch a `done` ticket *before* `_auto_activate` runs, so it is
never restarted. Surface = fail loud + generic reopen instruction (human
decision), not a `relay mark active <slug>` command hint, because the current
CLI still refuses `done -> active`. Draft/paused still activate inline.

Done case never reaches `_auto_activate` now, so the separate
assignee-not-re-resolved-on-reseed gap is unreachable via launch. A supported
done-ticket reopen path, including assignee re-resolution, is a separate
workflow decision.

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

## Peer Review

Native review command:

- `codex review --base main`

Must-fix findings:

- The refusal message suggested `relay mark active <slug>` as the reopen path,
  but the current CLI explicitly rejects `done -> active`.
- `launch.py` and both live/packaged `relay/architecture` contexts still taught
  that launch auto-activates `draft`/`paused`/`done` tickets.

Applied fixes in feature worktree commit `2adae6f`:

- Changed the done-ticket refusal to say reopening is deliberate, without naming
  an unsupported command.
- Synced `src/relay/commands/launch.py`, `relay-os/contexts/relay/architecture/SKILL.md`,
  and the packaged architecture copy under `src/relay/resources/templates/...`
  so launch only auto-activates `draft`/`paused`; `done` is refused and left
  untouched.
- Updated the launch test assertion for the new refusal wording.

Peer-review verification:

- `PYTHONPATH=$PWD/src python3.12 -m pytest tests/test_launch.py` — 66 passed
  (1 pytest cache warning from the read-only cache path).
- `PYTHONPATH=$PWD/src python3.12 -m pytest` — 806 passed, 1 skipped, 2 failed.
  Same unrelated `tests/test_autoclose_sweep.py` failures as above:
  live/packaged autoclose blackboard drift and `last_serviced_period:
  2026-06-17` vs expected `2026-06-11`.
- `git diff --check` — clean.
