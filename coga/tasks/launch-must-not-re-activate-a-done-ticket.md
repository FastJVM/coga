---
slug: launch-must-not-re-activate-a-done-ticket
title: Launch must not re-activate a done ticket
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/principles
- coga/architecture
- coga/codebase
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
secrets: null
---

## Description

`relay launch` on a `done` ticket silently restarts its workflow at step 1,
then crashes and leaves the ticket wedged. Launching a `done` ticket must not
re-activate it — it should refuse (or no-op) and leave the ticket untouched.

### Repro

```
$ relay launch <slug>          # ticket is done
Launch: task <slug> (status=done, mode=interactive, assignee=nick)
<slug>: active — auto on launch
Agent type 'nick' is not defined in [agents]. Known: ['claude', 'codex'].
```

### What goes wrong

`launch` brings any status outside `{active, in_progress}` to `active` inline
(`commands/launch.py:227-232` → `_auto_activate`), and that set **includes
`done`**. For a done ticket this calls `mark_active` →
`_freeze_workflow_ref` (`mark.py:208-211`), which re-seeds `step: 1` on the
re-activated ticket. So just typing `relay launch` a second time restarts a
finished workflow from the top.

It then crashes: re-seeding `step: 1` does not re-resolve `assignee:`, which
still holds the final step's resolved value (`nick`, the human `owner` from the
`review` step). Launch resolves the agent type straight from `assignee`
(`launch.py:277`, `cfg.agent_type("nick")`) → `Agent type 'nick' is not
defined`.

Worse, the failure is **not clean**: `mark_active` already wrote
`status: active` + `step: 1` and git-synced before the crash, so the ticket is
left wedged — `status: active, step: 1, assignee: <human>`. Re-launching now
skips `_auto_activate` (status is already `active`) and crashes again on the
same `agent_type` lookup. It does not self-heal without a hand-edit.

### Fix

`relay launch` must refuse to re-activate a `done` ticket. `_auto_activate`'s
status guard should exclude `done` so a done ticket is never restarted by a
launch. Decide the surface: a fail-loud error with a hint (e.g. "ticket is
done; `relay mark active` to reopen, or relaunch a different ticket") vs. a
quiet "nothing to do" no-op mirroring the freshness-check message. Draft /
paused re-activation is unchanged.

Note the separate `assignee`-not-re-resolved-on-step-reseed gap is real but
becomes unreachable for the done case once launch stops re-activating done
tickets; reopening is the deliberate `relay mark active` path, which can carry
its own assignee re-resolution if/when re-activation of a done ticket is wanted.

### Verification

- `relay launch <done-slug>` leaves the ticket `done` and unmodified (no git
  commit, no `step` reseed).
- Draft and paused tickets still activate on launch as before.
- A unit/CLI test covering launch-on-done.

## Context

Surfaced while debugging a `done` ticket that had been auto-bumped on PR merge
and then restarted by a second `relay launch`. The auto-bump-trigger half of
that story is tracked separately by
`v2/retire-standalone-relay-automerge-triggers-recurri` (move merge-detection
to the recurring `autoclose-merged` sweep, drop the launch-time freshness
check). This ticket is only the launch-restart guard and is independent of
where merge-detection lives.

<!-- coga:blackboard -->

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
