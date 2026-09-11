---
title: test_recurring_create_is_silent fixture fix is half-applied on main
status: draft
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

`tests/test_notification_messages.py::test_recurring_create_is_silent` fails
on `main` today. The fixture builds the task with `_make_task(..., force_directory=True)`
but then constructs `TaskRef(..., file_form=True)`, so `_broadcast_scan`'s period
lease reads a directory as a file and raises `IsADirectoryError` /
`NotADirectoryError` in `src/coga/recurring.py` before the notification
assertion is ever reached.

The reason this keeps being rediscovered is that the corpus contains a **claimed
fix**. `give-a-ticket-s-superseded-design-one-documented-h` (done) states under
`## Verification` that the test "passes in isolation after correcting its
fixture to use the directory-form shape guaranteed for recurring tasks" and
attributes the repair to commit `4012c5e9`. What actually reached `main` in
`c4482fae` was half of it: the fixture gained `force_directory=True` and an
explanatory comment, while the `file_form=True` on the `TaskRef` line was left
untouched.

So each rediscovery looks new. Four independent done tickets record the failure
as pre-existing on `main` and each says it is "worth its own ticket" —
`carry-adjacent-bugs-out-of-a-blackboard-before-ret`,
`dream-reconciliation-must-count-distinct-shard-ids`,
`live-and-packaged-twin-pairs-are-edited-together-b`, and
`a-slack-repo-without-important-webhook-can-abort-t` — and until now no
follow-up ticket existed and no context carried the evidence.

This is exactly the failure mode `carry-adjacent-bugs-out-of-a-blackboard-before-ret`
shipped a Retro rule to prevent, and its own adjacent bug is the one that
leaked. All four source tickets currently carry a recorded feature checkout, so
they are retirement debt rather than Retro input — but once retirement consumes
them, this ticket becomes the only record.

## Context

The fix is believed to be one token: `file_form=True` → `file_form=False` on
the `TaskRef` construction in `tests/test_notification_messages.py`. Confirm
that by running the test before and after rather than trusting the diagnosis —
the last recorded fix for this was also confident and also half-applied.

Any durable note about this must say the fix is **half-applied, not absent**;
that distinction is what stopped four previous readers from finishing it.

Verify with the absolute-`PYTHONPATH` invocation from a feature checkout
(`PYTHONPATH=$PWD/src python3.12 -m pytest tests/test_notification_messages.py::test_recurring_create_is_silent`),
because the editable install points at the primary checkout and a plain
`python -m pytest` from a worktree tests the wrong tree.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
