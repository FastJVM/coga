The blackboard is a notepad to be written to often as the human and agent works through a task.

## Origin

Split out of `relay-os/tasks/dream-5/` on 2026-05-08 by nick. dream-5
combined three concerns; this ticket is concern #3 — Dream is a
recurring task definition + an alias, not a Typer command.

Sibling tickets:
- `move-relay-delete-into-a-skill` (dream-5 concern #1)
- `make-dream-workers-skills-only` (dream-5 concern #2)

This ticket should land *after* the other two — it composes the
skills they produce.

## Open questions

- Alias expansion: does `relay recurring check` already support
  forcing a single template ("scaffold this one now")? If not,
  decide whether the alias triggers `recurring check` (which would
  scaffold every due template, surprising) or something narrower.
  Look at the existing `relay recurring` CLI surface before
  deciding.
- What about the existing `relay-os/recurring/_rem.md` (untracked
  in current working tree)? Confirm it's unrelated and that this
  ticket doesn't conflict with it.
- Existing `dream-*` tasks in `relay-os/tasks/` (5 of them as of
  2026-05-08): leave alone, or sweep under cleanup-orphan-markers
  later? Probably leave; flag in PR description.

## Prior art

- `7cf06b6` — Use recurring system for manual Dream triggering.
  Look at this commit's diff first; it's the closest thing to a
  reference implementation of what we're returning to.
- `ce67296` — Add ad-hoc Dream command (the one we're replacing).
- `8dda26e` — Stream claude stream-json output live during launch.
  Unrelated, but it's on top of the Dream commits, so check the
  rebase doesn't drop it.

## Implementation (2026-05-19, agent=claude)

Implemented on branch `compose-dream-recurring-alias` → **PR #177**
(https://github.com/FastJVM/relay/pull/177).

Resolved open questions:
- **Alias expansion.** `relay recurring check` only scaffolds *due*
  templates — no force-one verb existed. Added `relay recurring
  scaffold <name> [--launch]` (explicitly contemplated by the
  ticket's Proposed Shape and required by its acceptance criteria).
  The `dream` alias = `recurring scaffold dream --launch`. Factored
  `relay.recurring.scaffold_template` / `scaffold_named` so the cron
  `check` path and the on-demand `scaffold` path share one
  implementation and the same period-keyed (idempotent) slug.
- **`_rem.md`.** Unrelated — REM is user-space recurring maintenance;
  `dream.md` sits beside it as a separate live template. No conflict.
- **Existing `dream-*` tasks.** Left alone (flagged here, not in the
  PR — they predate this work and are Dream-run children/artifacts).

Shape delivered:
- `relay-os/recurring/dream.md` — live recurring template (weekly cron
  firing), body moved verbatim from the deleted `dream.md` resource
  into its `## Description` section. Shipped via `relay init` too.
- `dream` registered in `_DEFAULT_ALIASES` so it dispatches in repos
  whose `relay.toml` predates the line.
- `src/relay/commands/dream.py` + the `relay dream` registration +
  the `dream.md` prompt resource removed.
- Contexts/docs updated: `relay/cli`, `relay/architecture`,
  `relay/current-direction`, README, docs/design.md (`docs/spec.md`
  does not exist in this repo).

Tests: full suite 358 passed / 1 skipped; the lone failure
(`test_bump_unsupervised_prints_no_hint`) is pre-existing on `main`
and untouched here.

Workflow: `code/with-review` — implement step done; open-pr done
(PR #177). Awaiting the `review` step (assignee: owner).
