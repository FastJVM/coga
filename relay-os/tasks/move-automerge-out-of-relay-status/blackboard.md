The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: move-automerge-out-of-status
worktree: ../relay-move-automerge
pr: (pending — opened in the open-pr step)

## Origin

Discussed in an orient session on 2026-05-08. Nick noticed `relay status`
appeared to be mutating ticket state. Confirmed via `relay/cli` context:
`status` opportunistically calls `relay automerge` (quietly) as a
long-tail catch-up. Nick flagged this as the wrong place — read commands
should be reads, and the quiet-swallow of `gh` errors violates fail-loud.

Discussed alternatives:

- `cron.sh` hook next to `relay recurring check` — lightest, no ticket
  noise, but invisible runs.
- Recurring task — heavier (ticket per firing) but visible. **Picked
  this** for visibility and to fit the existing recurring primitive.
- REM responsibility — coupling automerge to a still-being-defined
  framework felt premature.

## Split

Originally bundled with a `relay launch <slug>` freshness check.
Split that out into a sibling ticket so each half can ship on its
own cadence:

- This ticket: the recurring sweep (replaces `status`'s implicit
  call). Has open design questions around cadence/noise.
- Sibling: `verify-ticket-freshness-on-relay-launch` — small,
  targeted check at launch time, can ship without waiting on the
  sweep design.

## Open

See `## Open questions` in `ticket.md`. Pick a workflow + schedule
when this leaves draft.

## Design decision (2026-05-21, with Nick) — SUPERSEDES the recurring-task plan

The ticket body originally said "move the sweep to a recurring task."
That is **dropped**. Nick walked the design further:

- **No recurring task, no cron in this ticket.** Cron-driven automerge
  is a planned *future* follow-up ("we'll add cron later").
- **`relay automerge` stays as-is** — it already sweeps every task in
  the right states (`active`/`in_progress`, final step or no workflow)
  and bumps only on PR state `MERGED`. No change to `automerge.py`
  logic. (Checked explicitly: merged-only, not closed-unmerged.)
- The **PR-in-blackboard** requirement is already met: every
  PR-producing workflow routes its PR step through `code/open-pr`,
  whose step 4 writes `pr: <url>` under `## Dev`. Nothing to fix.
- The **`post-merge` git hook** is also to be removed — but that is a
  distinct ~200-line change (`init.py`, `update.py`, `test_init.py`).
  Split into a sibling ticket `remove-post-merge-automerge-hook` so
  this ticket stays small and matches its title.

### Three-ticket structure (agreed)

1. `move-automerge-out-of-relay-status` — **this ticket.** Remove the
   `relay status` side-effect only.
2. `remove-post-merge-automerge-hook` — sibling draft (scaffolded).
3. add-cron-driven-automerge-sweep — future ("the plan").

## This ticket — scope

- `commands/status.py` — delete the opportunistic `auto_bump_merged`
  block + dead imports (`auto_bump_merged`, `TaskValidationError`).
- `automerge.py` — docstring only: drop `relay status` from the
  caller list; reword the `quiet` doc to not cite `relay status`.
- `tests/test_automerge.py` — delete the two `relay status` automerge
  tests; add a guard that `relay status` does not mutate ticket state.
- Doc sweep of the *status* reference only: `relay/cli` context
  (project-local + bootstrap + packaged), `README.md` automerge
  section, `dev/with-self-review.md` review-step text.
- Rewrite `ticket.md` body to the decided design.

Note: after this change `auto_bump_merged`'s `quiet=True` path has no
caller (only `quiet=False` via `relay automerge`). Left in place — the
sibling/cron tickets touch that area; removing it is optional cleanup,
not in scope here.

## Implement step — done (2026-05-21)

Changed (feature worktree `../relay-move-automerge`, branch
`move-automerge-out-of-status`):

- `commands/status.py` — dropped the opportunistic `auto_bump_merged`
  block + the `auto_bump_merged` / `TaskValidationError` imports.
- `automerge.py` — docstring only (caller list, `quiet` wording).
- `tests/test_automerge.py` — replaced the two `relay status`
  automerge tests with `test_relay_status_does_not_automerge`, which
  also stubs `pr_state` to fail loudly if `status` ever shells to gh.
- Doc sweep: `relay/cli` context (project-local + packaged copy),
  `README.md`, `dev/with-self-review.md` review-step text.

`init.py` lines 423/514 still say "`relay status` covers the gap" —
left untouched on purpose: that is hook code the sibling ticket
`remove-post-merge-automerge-hook` deletes wholesale.

Tests: 380 passed, 1 skipped. One pre-existing failure unrelated to
this change — `test_commands.py::test_bump_unsupervised_prints_no_hint`
fails identically on clean `main` (verified via `git stash`). Not
masked, not caused here.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: New principle: read-only commands must not mutate state
