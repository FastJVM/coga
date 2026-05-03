---
title: Clear step field when bump marks task done
status: active
mode: interactive
owner: nick
assignee: claude1
workflow:
  name: code/with-review
  steps:
  - name: implement
    skill: code/implement-and-pr
  - name: review
step: 1 (implement)
contexts:
  - relay/codebase
  - relay/cli
---

## Description

When `relay bump` advances past the last workflow step (or runs on a
workflow-less ticket), it sets `status: done` but leaves `step:` pinned
to the last step name. Result: done tickets carry contradictory state
on disk, e.g.

```
status: done
step: 2 (review)
```

A human reading the file (or the `relay status` table) sees "in review"
on the data plane and "done" on the control plane and has to know the
implicit rule "step is frozen on done" to reconcile them. Violates the
legibility principle in `relay/principles` — a single file should
mean one thing.

Also: once `status == done`, the step field carries no information
beyond what `workflow:` already implies (it can only ever be the
workflow's last step name). Denormalized, redundant state.

## Fix

In `src/relay/commands/bump.py`, both done-paths (lines ~54 and ~77)
should remove `step` from frontmatter alongside the `status = "done"`
flip:

```python
ticket.frontmatter["status"] = "done"
ticket.frontmatter.pop("step", None)
```

The audit value of "this task ended at step N" is preserved in
`log.md` (the `advanced to step N` entries), so nothing is lost.

## Out of scope

- Backfilling existing `done` tickets to drop their stale `step:`.
  Cheap one-liner if wanted, but the contradictory state on
  already-done tickets is a cosmetic wart, not a correctness issue.
  Defer unless the human asks.
- Changing `relay status` rendering. Once `step:` is absent on done
  tickets, the table will naturally show "—" or blank, which is the
  right outcome.

## Tests to update

- `tests/test_bump.py` — assert that after bumping the last step,
  `step` is absent from frontmatter (in addition to the existing
  `status == done` check). Cover both the workflow and no-workflow
  paths.

## Open question

Worth confirming with the human: do we also want a one-shot
backfill of existing done tickets in `relay-os/tasks/`? Two are
affected today (`diagnose-slack-notifications-not-firing-in-practic`,
`make-relay-panic-exit-non-zero`).
