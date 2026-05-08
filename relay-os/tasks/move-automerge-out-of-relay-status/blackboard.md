The blackboard is a notepad to be written to often as the human and agent works through a task.

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
