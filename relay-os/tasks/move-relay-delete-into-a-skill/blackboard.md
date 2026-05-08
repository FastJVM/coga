The blackboard is a notepad to be written to often as the human and agent works through a task.

## Origin

Split out of `relay-os/tasks/dream-5/` on 2026-05-08 by nick. dream-5
combined three concerns; this ticket is concern #1 — make `relay delete`
dispatch into a skill so deletion is no longer Relay-private Python.

Sibling tickets:
- `make-dream-workers-skills-only` (dream-5 concern #2)
- `compose-dream-as-recurring-plus-alias` (dream-5 concern #3)

## Open questions for the agent

- Should the CLI scaffold a real ephemeral `mode: script` task and call
  `relay launch` on it, or just call the skill's script directly with
  the same env contract? First option is more consistent with dream-5's
  "scripts are skills, never standalone" rule; second is faster and
  doesn't litter `tasks/` with throwaway directories. Pick and write the
  reasoning here before coding.
- Skill name: `bootstrap/delete-task` vs something shorter. Confirm with
  nick.
