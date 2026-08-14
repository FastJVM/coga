---
slug: unblock-rewind
title: unblock-rewind
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

Allow `coga bump <id> --to <N>` / `--backward` to rewind a ticket from `active`
and `paused` as well as `in_progress`. Today only `in_progress` is accepted, so
the only way to rewind an active ticket is to `coga launch` it and immediately
exit the REPL just to get the status flip.

The motivating case: the evaluator (or peer review) uncovers a legitimate design
change and the ticket needs to go through the implementation step again.

Rewind stays reposition-only — it moves `step:` and does not launch. `done`,
`canceled`, and `blocked` are explicitly out of scope (see Context).

## Context

### The rewind path already exists — only its status gate is wrong

`coga bump --to <N>` / `coga bump --backward` (`src/coga/commands/bump.py:42-51`)
already implements everything a rewind needs:

- human-only — agents are refused under `COGA_SUPERVISED` (`bump.py:71-76`), and
  told to `coga block` so a human decides;
- rewinds skip the `requires:` completion gate on the step being left
  (`bump.py:154`, `if not rewind and ...`);
- the target step's `assignee:` is re-resolved through `resolve_step_assignee`,
  so rewinding `peer-review → implement` hands the ticket back to the coder
  rather than leaving it on the peer (all four `code/with-review` steps declare
  `assignee:`);
- `advance_step(..., rewind=True)` relaxes exactly one validation guard
  (`allow_step_rewind`, `src/coga/bump.py:135`) and logs/broadcasts the
  transition as `rewound` rather than `advanced`.

The one thing blocking it is a guard that predates the rewind flags:

```python
# src/coga/commands/bump.py:92
if ticket.status != "in_progress":
    _bail(f"Task {ref.id_slug} is {ticket.status!r}. Cannot advance.")
```

That is right for a forward bump and wrong for a rewind. It is why an `active`
or `paused` ticket can only be rewound by launching it (which flips
`active → in_progress`, `launch.py:667-684`) and immediately exiting the REPL.

### Scope decided with the owner

- **No new verb.** Generalize the existing rewind path rather than adding
  `coga rewind`. The CLI spelling stays `coga bump <id> --to <N> / --backward`.
- **Rewindable statuses: `active`, `in_progress`, `paused`.** `done` and
  `canceled` are out of scope — see "Why `done` is excluded". `blocked` is
  also out of scope by owner decision — see "Blocked tickets must be unblocked
  first". A `draft` or workflow-less ticket has no step to rewind and must keep
  failing loud with the existing message.
- **Reposition only.** Rewind writes `step:` and stops. It does not launch;
  the human runs `coga launch` next. No `--launch` flag in this ticket.
- **`--backward` from step 1 stays a hard error** (`bump.py:132-133`,
  `"Task ... is on the first step. Cannot rewind."`). Owner-confirmed: this is
  current behavior and it is correct — there is no step 0, and clamping to
  step 1 would silently no-op. Keep the message and keep the test that
  covers it.

### Recommended design: rewind moves the step and never touches status

The obvious-looking move — normalize every rewound ticket to `active` — is
wrong, and the repo already says so. `src/coga/git.py`'s
`_ticket_state_regression_reason` documents the invariant *"a rewind never
changes status, so a status regression there means the checkout is stale, not
deliberate"*, and `allow_step_rewind` relaxes **only** the step rule. Concretely
(`git.py:136-142`, `git.py:2492-2503`): `_STATUS_PROGRESS` maps
`active: 1, in_progress: 2`, and a backward move is refused — so normalizing an
`in_progress` ticket to `active` would be rejected by the sync guard. (`paused`
has no `_STATUS_PROGRESS` entry at all, so it is not subject to that rule
either way.)

Leaving status alone sidesteps the whole problem and costs nothing, because
`coga launch` already accepts each rewindable status (`launch.py:251`):

- `active` → stays `active`; `coga launch` flips it to `in_progress`.
- `in_progress` → stays `in_progress` (today's behavior, unchanged).
- `paused` → stays `paused`; the human resumes with `coga launch`.

So the change is: split the `bump.py:92` guard so a *forward* bump still
requires `in_progress`, while a *rewind* accepts `{active, in_progress, paused}`
and rejects everything else with a clear message. If the implementer finds a
reason this doesn't hold, that is a design decision to escalate, not to paper
over by editing `git.py`.

### Blocked tickets must be unblocked first

Owner decision: a rewind of a `blocked` ticket **refuses outright** rather than
moving the step. The refusal must name the fix — something like:
"Task &lt;id&gt; is blocked. Run `coga unblock <id>` first, then rewind."

Rationale: `coga unblock` owns blocker resolution and already flips
`blocked → active` while resolving the open asks
(`src/coga/commands/unblock.py:237`). Letting rewind move the step of a blocked
ticket would leave a ticket sitting on a step it has been repositioned to with
an unresolved blocker still open on the blackboard — two commands writing
overlapping state with no single owner. Refusing keeps one owner per concern
and costs the human one extra command in a case that is already a stop-and-think
moment.

Rewind must **not** clear blockers as a side effect.

### Why `done` is excluded

The owner explicitly dropped it. Reopening a `done` ticket is not a gate
removal — three independent mechanisms defend it, one of them deliberately:

1. `mark_done` deletes the step (`src/coga/mark.py:139`,
   `ticket.frontmatter.pop("step", None)`), so `step_index()` is `None` and the
   rewind arithmetic at `bump.py:124-142` has nothing to count back from.
2. `validate` forbids `step:` on a terminal ticket (`src/coga/validate.py:968`),
   so status and step would have to be written in one pass — which
   `advance_step` cannot currently express.
3. The sync guard refuses any move off a committed terminal status
   (`git.py:2483-2489`), and there is a passing test defending exactly that:
   `tests/test_git.py:3977 test_bump_rewind_still_refuses_a_terminal_control_copy`.

Plus a live trap if it were allowed: a `done` ticket rewound to its *final* step
with status `active`/`in_progress` matches `autoclose._should_sweep`
(`src/coga/autoclose.py:235`) exactly, and its PR is already merged — so the
next sweep would re-close it within 24h.

Do not implement any of this. Do not weaken `git.py`'s terminal-status rule or
touch that test. If reopening a `done` ticket turns out to be needed, it is a
separate ticket.

### Out of scope

- A `coga rewind` alias or new Typer command.
- Rewinding a `done` or `canceled` ticket (above).
- Rewinding a `blocked` ticket (above) — and in particular, clearing blockers
  as a side effect of a rewind.
- Relaunching as part of rewind (`--launch`).
- Letting agents rewind. The `COGA_SUPERVISED` refusal stays: an agent that
  thinks a step needs redoing calls `coga block`, and the human rewinds.
- Any change to forward-bump semantics, including the `requires:` gate.
- Relaxing the step-1 `--backward` error.

### Repo notes

- Keep the Typer handler in `src/coga/commands/bump.py` thin; shared behavior
  belongs in `src/coga/bump.py` (`coga/codebase` microkernel rule). Note that
  the status-transition tables (`_ACTIVE_FROM` etc.) live in the *CLI* module
  `src/coga/commands/mark.py:46-49` behind a `sys.exit`-based
  `_check_transition`, so they are not a drop-in for reuse from `bump`. The
  recommended design above needs no transition table at all — if you find
  yourself promoting them to core (`src/coga/lifecycle.py` holds
  `VALID_STATUSES` / `TERMINAL_STATUSES` and would be the right home), that is
  scope growth worth flagging first.
- **Tests:** the rewind suite lives in `tests/test_commands.py` (lines 139-232,
  plus `test_bump_rewind_ignores_requires_gate:555` and
  `test_bump_rewind_resolves_target_step_assignee:1093`) and
  `tests/test_git.py:3952,3977`. `tests/test_mark.py` and `tests/test_cli.py`
  barely touch bump — don't look for it there. Add coverage alongside the
  existing suite in `tests/test_commands.py` for: rewind from each of
  `active` / `in_progress` / `paused`, the `blocked` refusal naming
  `coga unblock`, the `done` / `canceled` refusals, and the unchanged step-1
  `--backward` error.
- `test_bump_rejects_non_in_progress` (`tests/test_commands.py:457`) and
  `test_bump_error_wrong_status_does_not_signal` both exercise *forward* bumps
  on `paused`/`canceled`. Scoping the relaxation to `rewind=True` leaves them
  passing — they are correct as written, do not "fix" them.
- Verify with `python -m pytest` and `coga validate --json`.
- If behavior changes in a way the docs describe, update the matching text in
  `coga/contexts/coga/architecture/SKILL.md` (the step/status state machine)
  and its packaged copy under `src/coga/resources/templates/coga/` in the same
  PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
