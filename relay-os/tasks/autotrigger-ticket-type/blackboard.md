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

## Session 2 — model collapse + draft finalized

Worked the mental model with nick interactively. Landed on a tighter
formulation than session 1:

- **No new status needed.** `active` already means "approved, ready,
  waiting to be launched." `relay launch` owns the `active → in_progress`
  transition (src/relay/commands/mark.py). An autotrigger just makes a
  *trigger* the owner of that same transition instead of a human.
- **Launch and recurring are the same firing act.** Both move a ready
  (active) ticket → in_progress. They differ in ONE thing: whether a
  fresh ready ticket is re-stocked after `done`. one-shot = no re-stock;
  recurring = re-stock.
- **"auto" = system does a human gesture:** launch (one-shot) replaces
  `relay launch`; recurring replaces the recurring scaffold.

Wrote all of this into ticket `## Context` (definition + lifecycle +
re-stock table). Set `workflow: autonomy/assist-only` (design/vocabulary
deliverable — human owns the mental model; Q2 of triage fails).
contexts stay [] — body is self-contained.

Still draft. nick launches after review.

## Evaluator review

Independent cold review (Session 2). Verdict: solid concept ticket,
ready to launch — with one factual correction and two flags.

1. Clarity — yes. Crisp one-sentence definition, states what's unified
   and why-now, explicitly bounds to "concept-capture only." Two-axis
   model + ASCII lifecycle + "gesture it replaces" table do real work.

2. Workflow fit — correct. `autonomy/assist-only` is right: taste/
   judgment work, human owns the result, agent produces support
   material (agent-produces → human-owns-and-finishes). No mismatch.

3. Contexts — none attached; defensible but not free. Body argues from
   first principles. Could attach `principles/` + `architecture/` so the
   "no new status / no new daemon" claims are checkable rather than taken
   on faith. Minor gap.

4. Scope — reasonable and well-disciplined. Explicitly pushes impl,
   frontmatter syntax, migration, event/webhook out of scope. It's the
   umbrella the impl tickets hang under, not a build ticket.

5. Framing assumptions:
   - [FIXED] file citation was wrong: the active→in_progress flip is
     `mark_in_progress` in src/relay/mark.py, fired by relay launch
     (src/relay/commands/launch.py:286), NOT commands/mark.py (which only
     does active/paused/done). Claim itself (launch owns the transition)
     is accurate.
   - "recurring = re-stock after done" is a clean abstraction but glosses
     a flow that misfires today — see live tickets
     detect-recurring-runs-that-mark-done-without-advan,
     recover-recurring-runs-orphaned-when-the-superviso,
     fix-recurring-templates-not-instantiated. Fine for concept-capture; human
     shouldn't think re-stock is a solved trivial step.
   - [FIXED/annotated] the two "related tickets" slugs don't exist as
     task dirs; annotated in body as planned-not-created with pointers to
     the live recurring cluster.

Bottom line: clear, correctly scoped, right workflow. Pre-launch fixes
(a) file citation and (b) dangling slugs are done; (c) attaching
principles/+architecture/ is optional.
