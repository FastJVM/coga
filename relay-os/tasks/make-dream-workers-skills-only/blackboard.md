The blackboard is a notepad to be written to often as the human and agent works through a task.

## Origin

Split out of `relay-os/tasks/dream-5/` on 2026-05-08 by nick. dream-5
combined three concerns; this ticket is concern #2 — make every Dream
worker a plain skill, removing the side-channel "Dream worker" Python
shape.

Sibling tickets:
- `move-relay-delete-into-a-skill` (dream-5 concern #1)
- `compose-dream-as-recurring-plus-alias` (dream-5 concern #3)

## Inventory to do first

Before refactoring, list every place in the repo that imports or
references a Dream worker as Python (grep `from relay.commands.dream`,
`worker.main`, `validate-drift`, `cleanup-orphan-markers`, anything
under `src/relay/resources/dream/`). Write the list here so we know
what "done" means for the grep-proves-it acceptance criterion.

## Open question

Where do these skills live — `relay-os/skills/dream/...` or
`relay-os/bootstrap/dream/skills/...`? Probably the bootstrap tree
since they ship with Relay, but confirm by looking at where the
existing `bootstrap/dream/tasks/...` resources sit today.
