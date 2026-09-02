---
slug: megalaunch-activates-picks-before-preflight
title: Megalaunch activates picked tickets before its preflight checks refuse them
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (peer-review)
---

## Description

`coga megalaunch` durably flips a picked ticket to `active` before running the
preflight checks that can refuse it, so a ticket whose session never started is
left on disk claiming work began. This is the same invariant violation as the
sibling ticket `launch-activates-before-preflight` — *activation must not be
durable until every refusal has passed* — reached through different code.

In `src/coga/megalaunch.py`, Phase 2 of the pick loop calls
`_activate_for_launch` for any ticket whose status is in
`{"draft", "paused", "blocked"}` and appends it to `launch_plan`. Phase 3 then
launches the plan one entry at a time, and only there does
`_preflight_agent_launch` run `compose_prompt`, `build_launch_env`, and the
push-auth check — the same refusals that gate `coga launch`. A queue pick with
a malformed `secrets:` is therefore written to disk as `active`, with its
`workflow:` frozen, its `step:` seeded, and an
`activated (draft → active) — explicit megalaunch pick` line appended to
`coga/log.md`, and *only then* refused.

`_activate_for_launch` calls `mark_active` (`src/coga/mark.py`), which is the
durable wrapper: `prepare_active` → `ticket.write` → `assert_task_valid` →
`append_log` → `git.sync_task_state`. `prepare_active` is documented as the
"pure preparation boundary … without writing durable state" and is what the fix
should lean on, exactly as in the sibling ticket.

## Context

**Split from `launch-activates-before-preflight` on 2026-09-02.** It was briefly
folded into that ticket and split back out the same day: the two fixes share an
invariant and a helper (`prepare_active`), but no code and no edit shape. Fold
them back together only if that turns out to be wrong.

**Why this is not a copy of the sibling fix.** Three structural differences,
each verified by reading `src/coga/megalaunch.py`:

1. **Megalaunch re-reads each ticket from disk between activation and launch.**
   Phase 3 calls `read_ticket(ref)` per plan entry. The sibling ticket's
   technique — prepare in memory, carry the mutated `Ticket` across the
   preflights, commit at the end — *does not transfer*: a prepared-but-
   uncommitted mutation is discarded by that re-read. Either redo the prepare
   after the re-read, or reconcile the two. Do not try to carry an object
   across it.
2. **`_preflight_agent_launch` refuses on status.** It returns
   `f"status is {ticket.status}; expected active or in_progress"`, so it
   structurally depends on the durable activation having already happened. It
   has to accept a prepared/prospective view before activation can be deferred
   behind it, with the status check narrowed to what it actually exists to
   catch (a terminal or otherwise unlaunchable ticket).
3. **The batch shape is a decision, not an implementation detail.** Deferring
   per-ticket activation to just before that ticket's own launch means a ticket
   picked but never reached under `--max-tasks` is no longer activated. That is
   arguably the *desired* behavior, but it is a user-visible semantic change
   that must be chosen deliberately and asserted in a test.

**A trap that must not be broken.** `_activate_for_launch` has a second call
site, on the dependency-drain path, which activates *before* resolving open
blockers. That order is defended by a comment and is load-bearing: resolving
first would strand a blocked ticket with no open asks — a state that both
`coga launch` and `coga unblock` refuse and that blocker reminders no longer
report, so the owner would lose the ask instead of repairing it. Preserve this
ordering exactly, even if the prepare/commit split changes the call shape.

**Keep the sweep alive.** Unlike `coga launch`, megalaunch must not exit the
process on a refusal — `_activate_for_launch` returns a `MegalaunchResult`
(`skipped-unlaunchable` / `failed`) precisely so one bad task does not kill the
sweep. Its `except` ladder maps `WorkflowMissing`, `WorkflowError`,
`RequiredExtensionMissing`, `BlackboardNeedsSynthesis`, and
`TaskValidationError`. That contract survives the change.

**The exception seam.** `mark_active` calls `prepare_active` first and only then
writes, so the first four of those exceptions originate in the *prepare* half
while `TaskValidationError` comes from the post-write `assert_task_valid` in the
*commit* half. A prepare/commit split must divide the ladder along that seam —
do not leave a post-write handler on a pre-write helper.

`coga/launch-internals` is deliberately **not** attached: its own description
scopes it to tickets changing `launch.py`, the recurring runner, `open-pr`, or
the step gates, and this ticket changes none of those. The facts this work needs
are inline above.

## Acceptance Criteria

- [ ] A picked ticket whose `secrets:` is malformed — or which fails any other
      `_preflight_agent_launch` check — is reported as `skipped-unlaunchable`
      or `failed` with its status unchanged on disk: no
      `activated … — explicit megalaunch pick` line in `coga/log.md`, and no
      activation state commit.
- [ ] The same holds for the other refusals `_preflight_agent_launch` performs:
      unknown agent type, missing agent CLI, `ComposeError`, and failed push
      auth.
- [ ] One refused ticket does not end the sweep; the run continues to the next
      pick and the refusal appears in the run summary as it does today.
- [ ] The dependency-drain call site still activates *before* resolving open
      blockers, so a refused activation leaves the ticket `blocked` with its
      asks intact.
- [ ] The `--max-tasks` interaction is a stated, tested behavior: whether a
      picked-but-unreached ticket is left unactivated is asserted, not
      incidental.
- [ ] A successful pick is behaviorally unchanged: the ticket ends
      `in_progress` and the log still shows `activated` before `started`.
- [ ] The five activation refusals still map to the same `MegalaunchResult`
      outcomes and details they do today.
- [ ] `python -m pytest` passes; `coga validate --json` is clean.

## Proposed Shape

One file: `src/coga/megalaunch.py`. `prepare_active` and `mark_active` already
expose the boundary; no signature changes in `mark.py`.

1. **Split `_activate_for_launch` into prepare + commit**, dividing its
   `except` ladder along the prepare/commit seam described in `## Context`.
   Both halves keep the loud-result-not-exit contract.
2. **Teach `_preflight_agent_launch` to accept a prepared view**, narrowing its
   status check to terminal/unlaunchable rather than to the activation it is
   now upstream of.
3. **Move the Phase 2 activation into Phase 3**, per ticket: Phase 2 keeps
   selection and the prepared view, Phase 3 preflights and then commits the
   activation immediately before launching that same ticket. Handle Phase 3's
   `read_ticket(ref)` re-read explicitly — see `## Context` item 1.
4. **Leave the dependency-drain call site's ordering alone.**
5. **Decide and document the `--max-tasks` semantics** in code, and assert it.
6. **Tests** in the megalaunch test module: a picked draft with bad `secrets:`
   stays `draft` with no `activated` log line and a `skipped-unlaunchable`
   result; the sweep continues past it; the dependency-drain path still
   activates before resolving.

Cite symbols and guard conditions, not line numbers — the sibling ticket rotted
badly enough on line numbers to look retired twice.

## Out of Scope

- **The `coga launch` half.** Tracked in `launch-activates-before-preflight`.
  Land that first if both are in flight; this ticket does not depend on it, but
  the two should end up with the same prepare/commit shape.
- **The recurring runner's forced-run activation.** `recurring_runner.py`
  durably activates a period ticket before launch's preflights and its
  docstring defends that ("If the later launch preflight fails, the task is at
  least live for a future normal sweep"). Deliberate; untouched.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: megalaunch-defer-activation
worktree: /home/n/Code/claude/coga-megalaunch-defer-activation

## Owner decisions — 2026-09-02

1. **`--max-tasks`: unreached picks are left untouched.** Deferring activation
   to just-before-launch means a picked ticket the run never reaches keeps its
   `draft`/`paused`/`blocked` status, with no `activated …` log line. Chosen
   deliberately (it is what the invariant implies), documented in code, and
   asserted in a test.
2. **`_preflight_agent_launch`'s status check is narrowed**, per the spec's
   Proposed Shape: it now refuses terminal statuses instead of requiring
   `active`/`in_progress`. It is also *fed the prospective view*, so the
   composed prompt and env are the ones the launch will actually use.

## Design

- Phase 2 no longer writes. It builds a prospective `active` view with
  `prepare_active` on a copy of the ticket, reports the prepare-half refusals
  with today's outcomes/details, and runs the "no current workflow step" gate
  against that view. Plan entries carry `needs_activation`.
- Phase 3 re-reads (unchanged) and hands `_launch_until_stop` the flag. Per
  spec item 1, the prepare is **redone** from the freshly read ticket — no
  prepared object is carried across the re-read.
- `_launch_until_stop` commits the activation on its first step only, after
  `_preflight_agent_launch` has passed on the prospective view. This keeps the
  preflight running exactly once per launch: doing it in Phase 3 instead would
  cost a second `compose_prompt` and a second `git push --dry-run` probe per
  ticket, since `_launch_until_stop` preflights again on its own.
- Exception seam: `_prepare_for_launch` handles only the four prepare-half
  exceptions; `TaskValidationError` stays on the commit half in
  `_activate_for_launch`, which keeps its full ladder because the drain path
  calls it with no prior prepare. Both share one refusal-mapping helper so the
  five outcomes/details are identical to today.
- Drain path call order (activate, *then* resolve asks) is untouched.

## Implemented — commit `63086a43`

`src/coga/megalaunch.py` (plus the two `commands/megalaunch.py` help strings
that described the old phase names), and four tests in
`tests/test_megalaunch.py`.

- `_prepare_for_launch` — new prepare half. `prepare_active` on a throwaway
  `Ticket` copy; returns the prospective view or a `MegalaunchResult`. Handles
  only the four `prepare_active` exceptions.
- `_activation_refusal` — the shared mapping, so a refusal reads identically on
  either side of the write. `_activate_for_launch` keeps the full ladder
  (`*_PREPARE_ACTIVE_ERRORS, TaskValidationError`) because the drain commits
  through it with no preceding prepare, and `mark_active` re-runs
  `prepare_active` anyway.
- Phase 2 → **check**: prepares, reports, gates on `prepared.current_step()`.
  Writes nothing. `_PlannedLaunch(ref, blocked_resume, needs_activation)`
  replaces the 2-tuple plan entry.
- Phase 3 → activates inside `_launch_until_stop` (new `activate:` kwarg), on
  the first step only, between the preflight and `mark_in_progress`.
- `_preflight_agent_launch` status check narrowed to `TERMINAL_STATUSES`.

Two deliberate semantic changes beyond the refusal fix, both asserted:

1. A pick the run never reaches under `--max-tasks` is left unactivated
   (owner decision 1 above).
2. A pick that reached a terminal status while an earlier launch ran is
   reported `skipped-unlaunchable` instead of activated. This one is *forced*
   by the fix: deferral widens the pick→launch window, and `prepare_active`
   raises `CancellationError` on a canceled ticket — uncaught, that would have
   killed the sweep. Guarded at Phase 3's re-read.

### Tests

Four added; each of the first three was confirmed to fail against `main`'s
`megalaunch.py` and pass against the new one:

- `…_does_not_activate_pick_refused_by_preflight` — mapping-form `secrets:`,
  asserts byte-identical ticket, `status == "draft"`, no `activated` log line,
  and that the second pick still launched.
- `…_does_not_activate_pick_without_agent_cli` — the missing-CLI refusal.
- `…_leaves_picks_beyond_max_tasks_unactivated` — semantic change 1.
- `…_logs_activation_before_start` — unchanged happy path; passes on `main`
  too, which is the point.

`test_megalaunch_drain_keeps_ask_open_when_activation_refuses` still passes
unchanged: the drain's activate-then-resolve ordering was not touched.

### Verification

- `python -m pytest` — 2206 passed. One unrelated pre-existing failure,
  `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`, which
  fails identically on `main` in this environment (`No module named pip` in the
  venv). Not caused by this change; not fixed here.
- `coga validate --json` — output byte-identical to `main` (30 pre-existing
  issues, one of them an error on the unrelated `v2/autotrigger-ticket-type`
  draft). This change moves it neither way.
- No `example/` fixture change: task layout, prompt composition, and workflow
  semantics are untouched.
