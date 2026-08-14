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

Allow `coga bump <id> --to <N>` / `--backward` to rewind a ticket from `active`,
`paused`, and `blocked` as well as `in_progress`. Today only `in_progress` is
accepted, so the only way to rewind an active ticket is to `coga launch` it and
immediately exit the REPL just to get the status flip.

The motivating case: the evaluator (or peer review) uncovers a legitimate design
change and the ticket needs to go through the implementation step again.

Rewind stays reposition-only — it moves `step:` and does not launch. `done` and
`canceled` are explicitly out of scope (see Context).

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

That is right for a forward bump and wrong for a rewind. It is why an `active`,
`paused`, or `blocked` ticket can only be rewound by launching it (which flips
`active → in_progress`, `launch.py:667-684`) and immediately exiting the REPL.

### Scope decided with the owner

- **No new verb.** Generalize the existing rewind path rather than adding
  `coga rewind`. The CLI spelling stays `coga bump <id> --to <N> / --backward`.
- **Rewindable statuses: `active`, `in_progress`, `paused`, `blocked`.**
  `done` and `canceled` are out of scope — see "Why `done` is excluded".
  A `draft` or workflow-less ticket has no step to rewind and must keep
  failing loud with the existing message.
- **Reposition only.** Rewind writes `step:` and stops. It does not launch;
  the human runs `coga launch` next. No `--launch` flag in this ticket.

### Recommended design: rewind moves the step and never touches status

The obvious-looking move — normalize every rewound ticket to `active` — is
wrong, and the repo already says so. `src/coga/git.py`'s
`_ticket_state_regression_reason` documents the invariant *"a rewind never
changes status, so a status regression there means the checkout is stale, not
deliberate"*, and `allow_step_rewind` relaxes **only** the step rule. Concretely
(`git.py:136-142`, `git.py:2492-2503`): `_STATUS_PROGRESS` maps
`active: 1, in_progress: 2`, and a backward move is refused — so normalizing an
`in_progress` ticket to `active` would be rejected by the sync guard. `paused`
and `blocked` have no `_STATUS_PROGRESS` entry at all, so they are simply not
subject to that rule.

Leaving status alone sidesteps the whole problem and costs nothing, because
`coga launch` already accepts all four statuses (`launch.py:251`):

- `active` → stays `active`; `coga launch` flips it to `in_progress`.
- `in_progress` → stays `in_progress` (today's behavior, unchanged).
- `paused` → stays `paused`; the human resumes with `coga launch`.
- `blocked` → stays `blocked`, with its open blockers intact. `coga unblock`
  still owns blocker resolution and flips `blocked → active`
  (`commands/unblock.py:237`). Rewind must **not** silently clear blockers.

So the change is: split the `bump.py:92` guard so a *forward* bump still
requires `in_progress`, while a *rewind* accepts `{active, in_progress, paused,
blocked}` and rejects everything else with a clear message. If the implementer
finds a reason this doesn't hold, that is a design decision to escalate, not to
paper over by editing `git.py`.

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
- Relaunching as part of rewind (`--launch`).
- Letting agents rewind. The `COGA_SUPERVISED` refusal stays: an agent that
  thinks a step needs redoing calls `coga block`, and the human rewinds.
- Any change to forward-bump semantics, including the `requires:` gate.
- Clearing blockers as a side effect of rewinding a `blocked` ticket.

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
  barely touch bump — don't look for it there. Add rewind-from-each-status
  coverage alongside the existing suite in `tests/test_commands.py`.
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

## Evaluator review

## Independent review — `unblock-rewind`

Verified against `src/coga/commands/bump.py`, `src/coga/bump.py`, `src/coga/mark.py`, `src/coga/commands/mark.py`, `src/coga/git.py`, `src/coga/validate.py`, `src/coga/autoclose.py`, and the test suite.

### 1. Line/fact accuracy in `## Context` (the important part)

Correct:
- `src/coga/commands/bump.py:92-93` — the `status != "in_progress"` bail is exactly there, quoted verbatim. ✅
- `src/coga/bump.py:135` — `allow_step_rewind=rewind` is on that line. ✅
- Rewinds skip the `requires:` gate. ✅ (wrong line, see below)
- Target step's `assignee:` is re-resolved via `resolve_step_assignee` — ✅, and all four `code/with-review` steps declare `assignee:`, so `peer-review → implement` really does hand back to the coder.
- `launch.py:670-684` flips `active → in_progress` — ✅ (the guarding `if` actually starts at 667).

Wrong or stale:
- **`bump.py:68` for the `COGA_SUPERVISED` refusal is wrong.** Line 67-68 is the `--to`+`--backward` mutual-exclusion bail. The agent refusal is **`bump.py:71-76`**.
- **`bump.py:149` for `if not rewind and ...` is wrong** — line 149 is mid-comment. The real guard is **`bump.py:154`**.
- **`bump.py:42-53` for `--to`/`--backward`** is 42-51; 52-57 is the unrelated `--force` option.
- **"bump behavior is currently exercised from `tests/test_mark.py`, `tests/test_launch.py`, and `tests/test_cli.py`" is materially wrong.** `test_mark.py` mentions bump twice, `test_cli.py` once. The real homes are **`tests/test_commands.py`** (~101 references, including the entire existing rewind suite at lines 139-232 and `test_bump_rejects_non_in_progress` at 457), **`tests/test_git.py`** (the rewind/state-guard tests at 3952 and 3977), and **`tests/test_done_marker_emission.py`**. An implementer following the ticket would look in three near-empty files and miss the tests that actually constrain this change.
- **"the `autoclose-merged` recurring sweep and the digest both read status" — the digest does not.** `src/coga/commands/digest.py` contains no status read at all; it works off the spool. `autoclose.py:235` does read status (`{"active", "in_progress"}` + final step).

### 2. The central claim — "the one thing blocking it is a single guard" — is false for `done`

This is the biggest problem. Three independent mechanisms block a rewind out of `done`, none mentioned:

1. **`mark_done` deletes the step** (`src/coga/mark.py:139`, `ticket.frontmatter.pop("step", None)`). A `done` ticket has no `step:`, so `step_index()` is `None` → `current_idx = 0`. `--backward` then hits `Task ... is on the first step. Cannot rewind.` and `--to N` hits `Cannot skip ahead with --to.` The step arithmetic in `bump.py:124-142` needs real design work (and note `current_idx > total` bails at 126, so "synthesize `total + 1`" is not a free move either).
2. **`validate` forbids `step:` on a terminal ticket** (`src/coga/validate.py:968-973`: "`step:` must be absent when status is `done`"). `advance_step` writes `step:` and *only* `step:`/`assignee:`, then calls `assert_task_valid`. So status and step must be written in the same pass — `advance_step` currently has no way to express that.
3. **The git state guard explicitly refuses exactly this.** `src/coga/git.py:2483-2490` refuses any change away from a terminal committed status, and `_ticket_state_regression_reason`'s docstring says outright: *"a rewind never changes status, so a status regression there means the checkout is stale, not deliberate."* `allow_step_rewind` relaxes **only** the step rule. There is a passing test asserting this: **`tests/test_git.py:3977 test_bump_rewind_still_refuses_a_terminal_control_copy`**.

So "rewind from `done`" is not a gate removal; it is a deliberate reversal of a documented invariant in the sync layer, with a test defending it. The ticket should say so, and the owner should confirm that reversal is wanted before an agent starts editing `git.py`.

Also note `_STATUS_PROGRESS` (`git.py:136-142`) has **no entry for `paused` or `blocked`**, so those rewinds pass the status rule untouched — but `in_progress → active` is a 2→1 regression and *would* be refused. That directly bites the ticket's recommended landing status if the implementer normalizes an `in_progress` ticket to `active`. (The ticket's recommendation happens to avoid it — worth stating why, not by accident.)

### 3. Concrete traps not flagged

- **`mark_active` will clobber the rewind target.** `prepare_active` → `_freeze_workflow_ref` (`mark.py:409-416`) seeds `step: 1` whenever `ticket.step` is falsy. A `done` ticket has no step, so routing a done→active rewind through `mark_active` silently rewrites the step to 1 regardless of `--to`. Order of writes matters.
- **`_ACTIVE_FROM = {"draft", "paused"}`** (`commands/mark.py:46`) — it does *not* include `done`, `blocked`, or `in_progress`. "Reuse the transition tables" is not a drop-in; they'd have to be widened or bypassed. They also live in `src/coga/commands/mark.py` (a CLI module, with a `sys.exit`-based `_check_transition`), not `src/coga/mark.py` as the "Repo notes" imply. Reusing them from `bump` means promoting them to core (`src/coga/lifecycle.py` already holds `VALID_STATUSES` / `TERMINAL_STATUSES` and looks like the right home) — that's a real, unbudgeted refactor, and the microkernel note's "satisfied by construction" claim doesn't cover it.
- **Autoclose will re-close a reopened ticket.** A `done` ticket rewound to its final step (`review`) with status `active`/`in_progress` matches `autoclose._should_sweep` exactly, and the PR is already merged — the next sweep re-closes it within 24h. Rewinding out of `done` to a *non-final* step is safe; to the final step it is not. Nothing in the ticket says this.
- Good news: `test_bump_rejects_non_in_progress` and `test_bump_error_wrong_status_does_not_signal` both use *forward* bumps on `paused`/`canceled`, so scoping the relaxation to `rewind=True` leaves them passing. Worth stating explicitly so the implementer doesn't "fix" them.

### 4. Description clarity

Weak. It states the pain but never the deliverable — an agent has to infer "make `coga bump --to/--backward` work from more statuses" from `## Context`. 401 B of description against 4.2 KiB of context is inverted. One sentence would fix it: *"Allow `coga bump --to/--backward` to rewind a ticket from `active`/`paused`/`blocked`/`done`, not just `in_progress`, normalizing status to something `coga launch` accepts."*

Minor inconsistency: Scope says `canceled` is not rewindable; Open decisions then says `canceled` "must not survive a rewind." Pick one.

### 5. Missing context (given `contexts: []`)

The copy-facts-instead-of-attaching call was right, but two load-bearing facts are absent and would each cost an agent a wrong first attempt:
- `src/coga/git.py` `_ticket_state_regression_reason` / `_STATUS_PROGRESS` — the actual blocker.
- `src/coga/validate.py:968` — terminal status forbids `step:`.

Add those two paragraphs and the context is genuinely sufficient; the architecture context still isn't needed.

### 6. Scope

Reasonable *if* `done` is dropped or split out. `active`/`paused`/`blocked` → rewind is a contained change to `commands/bump.py` plus tests. Adding `done` pulls in `git.py`'s terminal-status invariant, a validate constraint, the transition tables' location, and the autoclose interaction — that is a second ticket's worth of judgment, and it's the half the description is actually motivated by (evaluator finds a design flaw). Recommend either splitting, or keeping it whole but rewriting `## Context` so the `done` path is presented as design work rather than a gate deletion.

### 7. Workflow fit

`code/with-review` is right. This touches shared step-movement and sync-guard invariants where a peer review pass has real value, and the final human `review` gate matters because the change weakens a safety invariant. No objection.

### 8. Composed-prompt proportions

One layer over 40%: **`base_prompt` (`prompt.md`) at 7.3 KiB ≈ 51% of the 14.4 KiB total.** It is more than half the prompt for a ticket whose own description is 2.7%. That's the standing base-prompt cost, not this ticket's fault, but at this ticket size it dominates — worth noting if base-prompt trimming is ever on the table. Everything else is proportionate: `task_context` 29%, `mode_prompt` 14%, the rest under 1% each. Total ~3.7k tokens is comfortable; the fix here is to add the two missing facts (§5) rather than to cut.

---

The blackboard is a notepad to be written to often as the human and agent works through a task.
