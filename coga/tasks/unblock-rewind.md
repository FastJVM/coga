---
slug: unblock-rewind
title: unblock-rewind
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
step: 2 (peer-review)
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

## Dev

branch: rewind-status-gate
worktree: /home/n/Code/claude/coga-rewind-status-gate

## Implement — what changed

Followed the recommended design in Context verbatim; nothing in it turned out
to be wrong, so no escalation was needed.

- `src/coga/bump.py` (core): added `REWINDABLE_STATUSES =
  {active, in_progress, paused}` and `rewind_status_error(id_slug, status)`,
  which returns the refusal string or `None`. The `blocked` case returns the
  owner-specified message naming `coga unblock <id>`; everything else
  (`draft`, `done`, `canceled`) gets "Cannot rewind. Rewindable statuses: …".
- `src/coga/commands/bump.py`: the single `status != "in_progress"` guard is
  now `if rewind: <rewind_status_error>` / `elif status != "in_progress"`.
  Forward-bump semantics, the `requires:` gate, the `COGA_SUPERVISED` agent
  refusal, and the step-1 `--backward` error are all untouched.
- No status write anywhere in the rewind path — `advance_step` still only
  writes `step:` (+ re-resolved `assignee:`), so `git.py`'s status rules stay
  armed and needed no edit. `paused` stays `paused`; the human resumes with
  `coga launch`.

Decision recorded: no transition table was promoted to `lifecycle.py`. The
design needs only a membership test, so `commands/mark.py`'s `_ACTIVE_FROM`
tables were left where they are (avoids the scope growth flagged in Context).

## Tests

Added alongside the existing rewind suite in `tests/test_commands.py`, reusing
its `_make_task` / `CliRunner` / `_log_text` style and a small
`_advance_then_set_status` helper (bump to step 2, then set the status on
disk — the shape a real rewind lands on):

- `test_bump_rewinds_from_rewindable_status` — parametrized over
  `active` / `in_progress` / `paused`; asserts step moves *and* status is
  unchanged.
- `test_bump_rewind_to_number_from_paused` — `--to` path, not just
  `--backward`.
- `test_bump_rewind_refuses_blocked_and_points_at_unblock` — with a real
  `append_blocker`; asserts the message names `coga unblock <slug>` and that
  step/status are untouched (no blocker cleared as a side effect).
- `test_bump_rewind_refuses_non_rewindable_status` — `done` / `canceled` /
  `draft`.
- `test_bump_backward_from_first_step_errors` — the step-1 error had no direct
  coverage in `tests/test_commands.py`; pinned it so the relaxation can't
  erode it later.

`test_bump_rejects_non_in_progress` and
`test_bump_error_wrong_status_does_not_signal` were left alone and still pass,
as Context predicted.

## Docs

Behavior described in prose, so updated in the same commit:

- `coga/contexts/coga/architecture/SKILL.md` + its packaged copy under
  `src/coga/resources/templates/coga/…` (verified byte-identical before and
  after): the data-plane bullet no longer says the step "only moves when
  status is `in_progress`"; it now states the forward/rewind split, the
  reposition-only rule, and the `blocked` → `coga unblock` refusal.
- `docs/reference.md` (`coga bump` section) and `docs/concepts.md` (step
  bullet) got the same distinction.
- `coga/contexts/coga/sync/SKILL.md` needed no change — "a rewind never
  changes status" is still exactly true, and this change is what keeps it so.

## Verification

- `python3.12 -m pytest` in the worktree: **1743 passed, 1 skipped**.
- `coga validate --json` against `example/coga`: `ok_count: 2`, no issues.
- `coga validate --json` against this repo's own `coga/`: 20 issues, all
  pre-existing on `main` (stuck-in-progress / unknown-assignee /
  unfrozen-workflow / draft-blackboard on unrelated `v2/*` tickets) and none
  touched by this branch.

Committed as `d84bc680` on `rewind-status-gate`, rebased on current
`origin/main`. Not pushed — that's the `open-pr` step.

## Peer review — blocked on sync-guard design

`codex review --base main` found a must-fix race and confirmed it with a
real-git reproduction:

1. A feature checkout holds `status: paused`, step 2, and stale blackboard
   text.
2. Another checkout resumes the control ticket to `status: in_progress`, moves
   it to step 3, and adds newer blackboard text (the same hole also permits a
   stale `active` copy to overwrite a newly `blocked` control ticket and erase
   its blocker).
3. The stale checkout runs `coga bump <id> --to 1`.
4. The new local status gate accepts `paused`. `advance_step(rewind=True)`
   disables the step-regression rule as intended, but `_STATUS_PROGRESS` has no
   entry for `paused` or `blocked`, so the remaining sync rules see no status
   regression. The control ticket is overwritten with stale `status: paused`,
   step 1, and the stale blackboard.

This disproves the ticket premise that leaving the local status untouched is
enough to keep the sync guard's status protections armed. The robust narrow
shape appears to be extending the rewind publication guard in `src/coga/git.py`
to require exact equality between the control and working statuses while still
allowing the deliberate step rewind. That is deliberately outside the approved
implementation scope: the ticket says a reason to edit `git.py` is a design
decision to escalate, not paper over.

Owner decision needed: approve the narrow `git.py` scope expansion (exact
control/local status equality for rewind publication), or choose a different
policy for stale `active` / `paused` rewinds.

Two documentation corrections are also required once the design is resolved:

- `architecture` and `docs/reference.md` say a rewind writes `step:` alone,
  but the established path also re-resolves and may rewrite `assignee:`.
- `coga/current-direction` still says rewinds/step movement only run while
  `in_progress`; update that live contract to the chosen behavior.

Review verification: targeted `tests/test_commands.py` **93 passed**; full
suite **1743 passed, 1 skipped**. Repo-wide `coga validate --json` reported
only the already-recorded unrelated task/config issues. The feature branch is
clean; no review fixes were committed and the required final rebase/open-PR
handoff were intentionally not performed while this design finding is open.

---

## Blockers

- [ ] [2026-08-13 22:51] [agent:codex] id=20260813T225158 Peer review reproduced a stale-state race: an active/paused rewind can overwrite a newer blocked/in_progress control ticket because rewind disables the step guard without requiring status equality. Please approve the narrow src/coga/git.py expansion to require exact control/local status equality for rewind publication, or choose a different stale-rewind policy.

---

## Blocker reminders

- 9ce2d8481594 last_reminded: 2026-08-14 10:59
