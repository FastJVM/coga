---
title: Dream sweeps done recurring period tickets
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/recurring
- relay/architecture
- relay/current-direction
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 4 (review)
---

## Description

Stage 3 of the recurring-lifecycle redesign in `relay/current-direction`
("Open redesign (recurring lifecycle: generate → done → Dream-deletes)").

Once `relay recurring` stops deleting anything (sibling ticket
`dream-recurring-persist-done-stop-inline-delete`), finished period tickets
sit on disk as `status: done`. Make **Dream** the single deleter that cleans
them up — the same retro-first pass that already deletes every other processed
`done` ticket (see `relay/current-direction` → "Done-ticket cleanup is
retro-first"). Recurring period tickets carry nothing durable (their output is
the Slack post / PR), so they direct-delete rather than route through retro
knowledge extraction.

Depends on the sibling ticket landing first (or merging together): if Dream
deletes `done` recurring tickets while the recurring command still self-deletes
and reaps, the two cleanup paths overlap.

## Acceptance Criteria

- A `done` `recurring-<name>-<period>` ticket is deleted by a Dream run via
  `relay delete` (working-tree `git rm` + commit), leaving the period ledger
  line behind so the period is not re-scaffolded.
- Each Dream period ticket (`recurring-dream-<period>`) is itself swept by the
  **next** Dream run — Dream no longer deletes itself mid-run.
- Verify the path: confirm whether Dream's existing `retro/done-ticket` /
  done-ticket cleanup already covers `recurring-*` tickets (knowledge-less →
  direct-delete) and only needs the self-delete special-case removed, OR a
  dedicated known-skill worker is needed. Document the decision on the
  blackboard and in `relay/recurring`.
- No double-delete / no error when a ticket is already gone (idempotent).
- `relay/recurring` and `relay/current-direction` updated to describe Dream as
  the recurring janitor; live + packaged copies in sync.
- `python -m pytest` and `relay validate --json` pass.

## Proposed Shape

- Investigate `relay-os/recurring/dream/ticket.md` (the Dream body lists its
  ordered known skills) and the `retro/done-ticket` skill to see if
  `recurring-*` done tickets already flow through cleanup. Prefer reusing the
  existing retro-first deletion over a new worker.
- If a dedicated worker is warranted, add it under
  `bootstrap/skills/bootstrap/dream/tasks/<name>/` with a Known Skill Contract
  (`Action: direct-fix`, `May change: done recurring-* task dirs`) and wire it
  into the Dream body's known-skill list.
- Tests: extend `tests/test_recurring.py` / Dream test coverage for the
  done-recurring-ticket deletion + ledger-preserved-skip path.

## Out of Scope

- Stages 1–2 (stop inline deletion, `--all` force-run, paused handling) —
  sibling ticket `dream-recurring-persist-done-stop-inline-delete`.
- Changing the retro knowledge-extraction model for ordinary (non-recurring)
  done tickets.

## Context

See `relay/current-direction` → "Open redesign (recurring lifecycle)" and
"Done-ticket cleanup is retro-first". `relay/recurring` documents the current
self-delete behavior being replaced.
