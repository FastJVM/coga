---
slug: always-accept-coga-ticket
title: always accept coga ticket
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow: code/with-review
secrets: null
---

## Description

`coga ticket <slug>` refuses to open a `blocked` ticket. `EDITABLE_STATUSES`
in `src/coga/commands/ticket.py` hardcodes six of the seven values in
`lifecycle.VALID_STATUSES`, omitting `blocked`, so the guard bails with a
misleading `unknown status 'blocked'; refusing guided ticket editing` — even
though revising the ticket is exactly how you resolve what blocked it.

Remove the status gate entirely rather than adding `blocked` to the list.
`coga ticket` runs no task work and moves no workflow: it opens an authoring
session over a markdown file the human already owns and can edit by hand.
Gating that on a `status:` value protects nothing and only creates a dead end.
Drop the informational `CAUTION_STATUSES` heads-up in the same pass — the
decision is that `coga ticket <slug>` opens any ticket, with no refusal and no
commentary.

Done looks like: `coga ticket <slug>` launches the authoring interview for a
ticket at **any** status, including `blocked` and an unrecognized/typo status,
printing nothing about the status.

## Context

### Where the change goes

All the gate logic lives in one file, `src/coga/commands/ticket.py`:

- `EDITABLE_STATUSES` (line ~43) and `CAUTION_STATUSES` (line ~51) — both
  delete, along with the explanatory comment above them.
- `_resolve_existing()` (line ~166) — the only consumer. Its `_bail` on
  unknown status and its `typer.secho` caution block both go; what remains is
  `read_ticket(ref)` and `return ref, ticket, False`. Update its docstring,
  which currently describes "gating on its status" and "the same status guard
  and caution heads-up."

Nothing else in the codebase references either constant (verified by grep).

### Why not keep the unknown-status bail

It is the one thing the guard also caught — a typo in `status:` frontmatter.
That belongs to `coga validate`, which already errors on any value outside
`VALID_STATUSES` (`src/coga/validate.py:573`). Refusing the authoring session
over it is backwards: authoring is the repair path for a malformed ticket.

### Tests that will break

Two tests in `tests/test_ticket.py` assert on the caution text and must be
updated, not deleted — they still assert the useful thing (the session
launches and `status:` is left unchanged), just without the note:

- `test_ticket_edits_in_progress_task` (line ~423) — asserts `"in_progress"`
  appears in the output.
- `test_ticket_can_edit_canceled_task_without_reopening` (line ~449) —
  asserts `"already canceled"` appears in the output.

Add a test covering the actual bug: a `blocked` ticket opens, exit code 0, and
its status is still `blocked` afterward. `_allow_ticket_launch` is the
existing helper for stubbing the spawn.

### Skill text to keep in sync

`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`
enumerates the editable statuses in its greeting section (line ~85, "at any
editable status (`draft`, `active`, ...)" and the caution sentence at line
~95). Both need updating to match. There is no live `coga/` mirror of this
particular skill — the packaged copy is the only one, so the usual
check-both-copies rule (CLAUDE.md) resolves to a single edit here.
`tests/test_bootstrap_ticket_skill_template.py` does not assert on the status
list, so it should keep passing.

### Out of scope

- `coga launch`'s own status handling — it legitimately refuses a `done`
  ticket, and that gate stays.
- Anything that changes a ticket's status. Editing a blocked ticket leaves it
  blocked; `coga unblock` remains the human's explicit call.
- `docs/reference.md` — its `coga ticket` entry (line 40) does not enumerate
  statuses, so it needs no change.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
