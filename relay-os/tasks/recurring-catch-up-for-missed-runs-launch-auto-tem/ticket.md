---
title: 'recurring: catch-up for missed runs + launch auto templates interactively'
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/cli
- relay/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Two changes to `relay recurring` (`src/relay/commands/recurring.py` +
`src/relay/recurring.py`). Both alter deliberate current behavior, so the
matching contexts (`relay/architecture`, `relay/cli`) and any README/spec
text must be updated **in the same PR** (per CLAUDE.md).

### Change 1 — catch up on missed runs (configurable cap, default 1)

Today `scan_due` is strictly "current period only": it get-or-creates only
*this* period's task and never chases periods that were missed because nobody
ran `relay recurring` in time. Running a weekly template once a month produces
one run, not the three that were skipped. This is documented as intentional in
`relay/architecture` and `relay/cli` ("Current period only … does not chase
missed periods").

We want bounded recovery instead:

- When prior scheduled periods were missed (no task scaffolded in the
  template's period ledger / blackboard for those periods), scaffold and launch
  catch-up runs for them, **oldest-first**, so the bare sweep heals a gap.
- Bound it with a **configurable cap** on how many missed periods to recover,
  **default 1** (recover only the most recent missed period unless raised).
  This prevents a backlog stampede after a long outage while still defaulting
  to "don't silently drop everything."
- Surface the cap in config. Likely a `[recurring]` key in `relay.toml`
  (e.g. `max_catchup = 1`); confirm the exact name/location during design and
  document it in the spec + `relay/cli`. If a real cap is exceeded, **log what
  was dropped** (don't silently truncate — principle 6, fail loud).
- The period ledger (template `blackboard.md`, `_record_run`) is the source of
  truth for "did this period already run" — reuse it to compute the missing
  set; don't double-scaffold a period that already has a task (idempotency must
  hold).

Design question for the design step: how period keys + `_last_firing` /
`_period_key` enumerate the missed-period set for cron-style schedules, and
whether catch-up runs share the sweep's sequential + idle-timeout machinery
(they should).

### Change 2 — launch `mode: auto` templates interactively instead of skipping

Today `_effective_mode` (`src/relay/recurring.py`) **raises** `RecurringError`
on any `mode: auto` template, so the auto-ban skips it entirely (loud stderr +
Slack scan-error). We want auto templates to still run, coerced to an
**interactive** launch.

- In the recurring scan/launch path, treat `mode: auto` as `interactive`
  (mode override at launch time, **without** rewriting the ticket file — same
  ephemeral-override pattern `--interactive` already uses).
- **No-TTY behavior: hard error.** If an auto template is coerced to
  interactive but stdin/stdout are not both terminals, fail loud and exit
  non-zero (do **not** skip silently). This is the chosen semantics: an
  unattended `relay recurring` that includes an auto template is a real
  misconfiguration and should surface, not pass quietly. Confirm during design
  that this doesn't wedge the sequential sweep mid-way without a clear message.
- This narrows/replaces the temporary auto-ban in `_effective_mode`. Update the
  comment there and the "`mode: auto` temporarily skipped" language in
  `relay/cli` + README accordingly.

### Also (small, in-scope)

`relay recurring --all` short-circuits before reading `--interactive`
(`recurring.py:85`), so `--all --interactive` silently ignores the flag.
And `--mode` is not a `recurring` flag at all (it's a `relay launch` flag), so
`relay recurring --all --mode interactive` is just an unknown-option error.
Decide whether to (a) reject the ignored/duplicate combination loudly, or
(b) leave as-is and document — but don't leave it silently ignored.

### Acceptance

- Bare `relay recurring` recovers up to the configured cap of missed periods,
  oldest-first, idempotently, with a log line when runs are dropped past the
  cap.
- `mode: auto` templates launch interactively under a TTY; hard-error
  (non-zero) with a clear message when no TTY is present.
- Contexts (`relay/architecture`, `relay/cli`), README, and `docs/spec.md`
  updated to match; live `relay-os/` copies and packaged
  `src/relay/resources/templates/relay-os/` copies kept in sync.
- Tests under `tests/` cover: catch-up enumeration + cap, idempotent re-run,
  auto→interactive coercion, and the no-TTY hard error.

## Context

The current "current period only" semantics and the temporary `mode: auto`
ban are both documented as intentional in the canonical contexts — this ticket
deliberately changes both, so the contexts move with the code. Decisions
already settled with the owner: catch-up = **configurable cap, default 1**;
auto-with-no-TTY = **hard error (exit non-zero)**.

