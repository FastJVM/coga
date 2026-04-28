The blackboard is a notepad to be written to often as the human and agent works through a task.

## Session 1 — concept capture

Goal of the ticket (per nick, interactive): define a unified
**autotrigger** ticket type that subsumes both today's recurring
templates and the proposed `idle-eligible` flag. Some autotriggers
recurring, some one-shot. The ticket is **draft only** — no
implementation lands here, just locking the mental model.

### Decisions made this session

- Autotrigger is the umbrella; recurring becomes a flavor of it
  (`cardinality: recurring` + `triggers: [{type: schedule, …}]`).
- Idle/budget-aware execution is also a flavor (`type: idle`).
- Trigger condition and cardinality are orthogonal.
- Multiple triggers on one ticket OR together (default semantics).
- Implies an orchestration layer, but no new daemon required —
  cron handles time triggers, idle triggers run in-session.

### Skill note

`bootstrap/ticket` is referenced in the frontmatter but the SKILL.md
does not exist (`relay-os/skills/bootstrap/` only has `dream/`).
Followed the `_template/ticket.md` structure instead: just
`## Description` and `## Context`, kept tight. Worth opening a
follow-up to actually write the bootstrap/ticket skill so future
draft-fleshing sessions have guidance.

### Open threads for next session

- Frontmatter syntax — the YAML sketch in earlier draft was
  illustrative. Final shape belongs in an implementation ticket.
- Migration plan for `relay-os/recurring/` once autotrigger lands.
- Whether `mode: auto` is implied or independent for autotrigger
  tickets.
