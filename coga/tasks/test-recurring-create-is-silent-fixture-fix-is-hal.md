---
title: test_recurring_create_is_silent fixture fix is half-applied on main
status: done
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

## Already satisfied

This ticket's own fix merged as `589e141a` (PR #780, "Finish the half-applied
test_recurring_create_is_silent fixture fix"), whose commit message names this
slug as closed. The ticket was created (`a33b9aa5`) before that PR landed and
was never marked done, so this launch found finished work rather than a bug.

Per-item evidence, checked on current `main` (`git status` clean):

- **One-token flip landed.** `tests/test_notification_messages.py` line 371
  now reads `ref=TaskRef(slug=slug, path=path, file_form=False)`. `git log -S"file_form=False" -- tests/test_notification_messages.py`
  returns exactly `589e141a`; `c4482fae` is confirmed as the half-fix (added
  `force_directory=True` and the comment, left `file_form=True`).
- **Test passes with the ticket's prescribed invocation.**
  `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_notification_messages.py::test_recurring_create_is_silent`
  → `1 passed`. (System `python3.12` lacks `tomlkit`; the repo `.venv`
  is the `.[test]` interpreter on this machine.)
- **Assertion is load-bearing, not vacuous.** Mutating it to
  `assert posts == ["MUTANT"]` fails with `assert [] == ['MUTANT']`, so
  `_broadcast_scan` runs to completion and posts nothing. Mutation reverted.
- **"Half-applied, not absent" is recorded durably.** The extended comment
  above the fixture (also from `589e141a`) says the two lines must agree and
  names the `IsADirectoryError` path; the `589e141a` commit message carries
  the full half-fix history (`4012c5e9` claim → `c4482fae` half → `589e141a`
  finish). No Coga context mentions it; `retro/done-ticket` decides whether
  the pattern deserves a context entry when it retires this ticket.

No branch, worktree, or PR created; closing with `coga mark done`.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: New context: a done ticket's fix claim can be half-applied on main — verify the exact token
