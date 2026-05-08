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
