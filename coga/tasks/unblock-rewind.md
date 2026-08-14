---
slug: unblock-rewind
title: unblock-rewind
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
---

## Description

There needs to be a cleaner way to rewind the ticket. Sometimes the evaluator uncovers legitimate design changes for which you'll want to go through the implementation stage again.

Now, the only way you can do it is by launching and immediately exiting the REPL to put the ticket back in_progress.

You should be able to rewind an active ticket (or really a ticket in any state.)

## Context

### The rewind path already exists — only its status gate is wrong

`coga bump --to <N>` / `coga bump --backward` (`src/coga/commands/bump.py:42-53`)
already implements everything a rewind needs:

- human-only — agents are refused under `COGA_SUPERVISED` (`bump.py:68`), and
  told to `coga block` so a human decides;
- rewinds skip the `requires:` completion gate on the step being left
  (`bump.py:149`, `if not rewind and ...`);
- the target step's `assignee:` is re-resolved through `resolve_step_assignee`,
  so rewinding `peer-review → implement` hands the ticket back to the coder
  rather than leaving it on the peer;
- `advance_step(..., rewind=True)` relaxes exactly one validation guard
  (`allow_step_rewind`, `src/coga/bump.py:135`) and logs/broadcasts the
  transition as `rewound` rather than `advanced`.

The one thing blocking it is a single guard that predates the rewind flags:

```python
# src/coga/commands/bump.py:92
if ticket.status != "in_progress":
    _bail(f"Task {ref.id_slug} is {ticket.status!r}. Cannot advance.")
```

That is right for a forward bump and wrong for a rewind. It is why an `active`,
`paused`, `blocked`, or `done` ticket can only be rewound by launching it (which
flips `active → in_progress`, `launch.py:670-684`) and immediately exiting the
REPL.

### Scope decided with the owner

- **No new verb.** Generalize the existing rewind path rather than adding
  `coga rewind`. The CLI spelling stays `coga bump <id> --to <N> / --backward`.
- **Any status that has a frozen workflow may be rewound** — `active`,
  `in_progress`, `blocked`, `paused`, `done`. Rewinding out of a terminal
  status is a legitimate reopen (the evaluator-found-a-design-flaw case).
  A workflow-less or `draft` ticket still has no step to rewind to and must
  keep failing loud with the existing message.
- **Reposition only.** Rewind writes `step:` (and normalizes `status:`) and
  stops. It does not launch; the human runs `coga launch` next. No `--launch`
  flag in this ticket.

### Open decisions for the implementer

- **What status does a rewound ticket land in?** The recommended answer is
  `active` for anything that was not already `in_progress` (it is repositioned
  and queued, not running), and leave an `in_progress` ticket `in_progress`.
  Whatever is chosen, `done`/`canceled`/`blocked`/`paused` must not survive a
  rewind — a rewound ticket has real work ahead of it, so the status must be
  one `coga launch` accepts.
- The status-transition rules live in `src/coga/commands/mark.py`
  (`_ACTIVE_FROM` / `_PAUSED_FROM` / `_DONE_FROM` / `_CANCELED_FROM` +
  `_check_transition`). Reuse or mirror them; do not fork a second parallel
  notion of which transitions are legal.
- Reopening a `done` ticket has side effects worth checking before writing
  code: the `autoclose-merged` recurring sweep and the digest both read status,
  and `mark_done` does a stranded-product-code check that a reopen may need to
  reverse or ignore.
- The log line and Slack broadcast already say `rewound`; make sure a rewind
  out of `done` also reports the status change, not just the step change.

### Out of scope

- A `coga rewind` alias or new Typer command.
- Relaunching as part of rewind (`--launch`).
- Letting agents rewind. The `COGA_SUPERVISED` refusal stays: an agent that
  thinks a step needs redoing calls `coga block`, and the human rewinds.
- Any change to forward-bump semantics, including the `requires:` gate.

### Repo notes

- This is an edit to an existing core command, so the microkernel rule
  (`coga/codebase`) is satisfied by construction — keep the Typer handler in
  `src/coga/commands/bump.py` thin and put shared behavior in `src/coga/bump.py`
  or `src/coga/mark.py` alongside the existing helpers.
- There is no `tests/test_bump.py`; bump behavior is currently exercised from
  `tests/test_mark.py`, `tests/test_launch.py`, and `tests/test_cli.py`. Add
  focused coverage for rewind-from-each-status, ideally in a new
  `tests/test_bump.py`.
- Verify with `python -m pytest` and `coga validate --json`.
- If behavior changes in a way the docs describe, update the matching text in
  `coga/contexts/coga/architecture/SKILL.md` (the step/status state machine)
  and its packaged copy under `src/coga/resources/templates/coga/` in the same
  PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
