---
title: blackboard for recurring task must use the permant one
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/recurring
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
---

## Description

Teach scaffolded period tasks that persistent state lives in their parent
recurring task's blackboard, not their own. Today the convention is documented
in `relay/recurring` (read by recurring-task authors), and individual recurring
bodies — `relay-dev-update/ticket.md` is the example — hand-roll a "Step 1 —
state lives in `relay-os/recurring/<name>/blackboard.md`" paragraph to teach
each launched run. That duplicates the rule per recurring task and is easy to
forget for the next one.

Fix this by auto-attaching a small context to every scaffolded period task at
scaffold time. The context carries the rule and the path derivation; the
recurring task body no longer has to teach it inline.

Concretely:

1. **New context `relay/period-task`** — one short page, focused on the
   per-period agent. It covers: you are a period instance scaffolded by
   `relay recurring`; your slug is `<parent-name>-<period_key>`; your parent
   recurring task lives at `relay-os/recurring/<parent-name>/`; persistent
   state for the recurring task is its parent's `blackboard.md` (read it at
   the start, update it before `mark done`); do **not** write last-run state
   to your own per-period `blackboard.md` — that is gone next period.
2. **Scaffolder change** in `src/relay/recurring.py`. `scaffold_template`
   passes `contexts=list(template.frontmatter.get("contexts") or [])` to
   `scaffold_task` (currently line ~275). Append `"relay/period-task"` to
   that list before the call, skipping the append if the recurring task
   already lists it explicitly (idempotency). Always-append is the right
   default here — the convention applies to every period task by definition,
   so an opt-out flag would just be a footgun.
3. **Trim `relay/recurring`** — it currently has a "Last-run state lives in
   the recurring task's blackboard" section aimed half at authors, half at
   the launched run. Keep the author-facing framing (what to put in the
   recurring `ticket.md` body, the gotcha about `relay-os/tasks/<...>/`
   blackboards being fresh) and point to `relay/period-task` for the
   per-run procedure.
4. **Drop the hand-rolled paragraph** from `relay-os/recurring/relay-dev-update/ticket.md`
   "Step 1 — Find where the last run stopped" and "Step 5 — Record state
   and finish" — collapse them so the body only describes the dev-update
   work itself, relying on the auto-attached context for the convention.
   The body still has to name *which* keys it persists (e.g. `last_commit`)
   — just stop re-teaching where the blackboard lives. `_rem` and
   `recurring/dream` were checked and do not hand-roll the rule today
   (`_rem` just notes "blackboard.md persists state"; `dream` writes
   per-run findings, not cross-run state), so no edits there.
5. **Tests** — extend `tests/test_recurring.py` (or the relevant scaffold
   test) to assert that a scaffolded period task's `contexts:` includes
   `relay/period-task`. Run `python -m pytest` and `relay validate --json`.

## Context

- Source of truth on the convention today: `relay-os/contexts/relay/recurring/SKILL.md`,
  specifically the "Last-run state lives in the recurring task's blackboard"
  section and the "Gotchas" bullet about per-period blackboards being fresh.
- Live example of the hand-rolled pattern this ticket eliminates:
  `relay-os/recurring/relay-dev-update/ticket.md` (Step 1 and Step 5).
- Scaffolder lives in `src/relay/recurring.py`; `scaffold_template` and
  `scaffold_named` call `scaffold_task` from `src/relay/scaffold.py`. The
  `contexts:` passthrough comes from the recurring `ticket.md` frontmatter
  today — the new behavior should append `relay/period-task` on top of
  whatever the recurring task already declared, idempotently (don't double-add
  if a recurring task already lists it explicitly).
- Per `CLAUDE.md`: when shipped contexts change, update both the live copy
  under `relay-os/contexts/` and the packaged copy. The packaged Relay
  contexts ship from `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/`
  (the `bootstrap/` subdir, not the top-level `contexts/` directory — that
  one only holds `_template/`). New `relay/period-task` needs a SKILL.md in
  both trees.
- Slug → parent-name derivation: period_key is one of `YYYY-MM-DD-HH`,
  `YYYY-MM-DD`, `YYYY-Www`, `YYYY-MM`. The new context should explain the
  rule plainly ("strip the trailing period suffix") and trust the agent;
  no need to over-specify a regex.
- Out of scope: changing how `recurring/_rem` or `recurring/dream` work
  structurally; reworking `relay/recurring` beyond the trim described in
  step 3; introducing a `recurring_parent:` frontmatter field (we
  considered it; the slug already encodes the parent).
