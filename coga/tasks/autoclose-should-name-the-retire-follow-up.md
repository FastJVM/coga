---
slug: autoclose-should-name-the-retire-follow-up
title: Autoclose should name the retire follow-up
status: in_progress
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

`coga autoclose` bumps a ticket to `done` when its `## Dev` PR merged, and then
nothing points at the next step. Checkout disposal belongs to `coga retire`
(it owns the linked-worktree / open-PR / landed-branch proofs), but retire is a
human-typed command — so an auto-closed ticket's feature worktree and branch
outlive the ticket silently, and by the time anyone notices, the ticket's
`## Dev` lines may already be gone.

Make the debt visible without making autoclose destructive: after a sweep,
report the closed tickets that still have a `worktree:` or `branch:` recorded,
with the exact `coga retire <slug>` command for each. Two surfaces to cover:

- the recipe's stdout / blackboard report (`## Dream Skill:`-style section when
  run under a task);
- the per-ticket Slack line, or one trailing summary line for the sweep — a
  decision to make in design, since the existing `🎉 ... merged` line is
  per-ticket and a retire hint per row may be noisy.

Explicitly out of scope: autoclose deleting anything. It should stay a
lifecycle sweep; duplicating retire's safety proofs (same-repo linked worktree,
no other live ticket sharing it, no open PR for the head, branch landed or
equal to the recorded merged head, tracked/untracked/ignored files preserved)
would either copy that machinery or ship a weaker version of it, and implicit
destruction cuts against the principle that destructive behavior is never
implicit.

## Context

Found while auditing seven leftover worktrees under `~/Code/claude/` on
2026-08-14. `coga run autoclose` closed five tickets in one pass; three of the
worktrees on disk belonged to tickets that had already been closed and deleted,
with no trace left of which command should have cleaned them up.

Related but separate: `coga retire` refuses worktree removal when the checkout
holds ignored files, and every dev worktree accumulates `.pytest_cache/` and
`__pycache__/` from the workflow's own test runs — so retire's cleanup half
currently no-ops on nearly every real code ticket. That is its own ticket, not
this one.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: autoclose-retire-hint
worktree: /home/n/Code/claude/coga-autoclose-retire-hint

## Design decision — Slack surface

The ticket left the Slack shape open. Asked the owner in the launch REPL on
2026-08-14; they chose **one trailing sweep summary**, not a per-ticket hint.

Rationale: the existing `🎉 ... merged` line is a *lifecycle* event and usually
lands in the daily digest (`mark_done` → `notification.notify`, spooled when
`recurring/digest/` is installed). A retire hint is an *operational to-do* with
a different audience and urgency; appending it to every Done row turns the
digest's Done section into a command list and buries the action item. One
trailing line is a single message regardless of sweep size and is suppressed
entirely when nothing needs retiring.

Accepted tradeoff: the summary is a live `notification.post` (the `notify`
kinds are restricted to `done`/`canceled`/`recurring-error`, and a sweep-level
summary is none of those), so it arrives at the 8am sweep rather than in the
9am digest, and a large sweep produces one long line.

## Plan

1. `sweep_merged` returns a result dataclass instead of a bare `int`, following
   `branchsweep.BranchSweepResult`: the tickets this run closed, each with the
   `branch:` / `worktree:` recorded under `## Dev`. Test call sites move to
   `len(result.closed)`.
2. `_try_bump_one` reads the blackboard once and parses `pr:` / `branch:` /
   `worktree:` from that single read (today `_read_pr_url` reads and discards
   the rest).
3. `run_autoclose_recipe` renders a `## Autoclose Sweep` report naming the exact
   `coga retire <slug>` per closed ticket with leftover checkout state —
   appended to the task blackboard via `task_env.blackboard_from_env` when run
   under a task, stdout otherwise. Written only when there is debt, so quiet
   days don't grow the recurring task's blackboard forever.
4. Trailing Slack summary as decided above, same suppression rule.
5. Autoclose deletes nothing — out of scope per the ticket, and duplicating
   retire's safety proofs would ship a weaker version of them.

## What landed

Commit `6dc68c9e` on `autoclose-retire-hint`, all five plan items as written.

- `src/coga/autoclose.py`: `ClosedTicket` / `AutocloseResult`, `sweep_merged`
  returns the latter, `_try_bump_one` reads the blackboard once and returns the
  closed ticket, `render_retire_report` / `render_retire_summary` /
  `_report_retire_followups`, wired into `run_autoclose_recipe`.
- `src/coga/task_env.py`: `append_blackboard_report`, next to
  `blackboard_from_env` which already resolves *where* a recipe's report goes.
- Docs kept in step with behavior (live + packaged copies both): the
  `coga/autoclose/sweep` skill, the `autoclose-merged` recurring template and
  workflow, and the `dev/code` context's list of `## Dev` consumers.
- Tests: `tests/test_autoclose.py` gains sweep-level capture of checkout state,
  pure renderer tests, and three recipe-surface tests (stdout + Slack,
  silence when nothing stranded, blackboard append). Existing `sweep_merged`
  call sites moved to `len(result.closed)`.

Verified: `python -m pytest` — full suite green on the rebased branch, 1749
passed / 1 skipped. `coga validate --json` — issue set identical to `main`
apart from the gitignored `coga.local.toml` missing in a fresh worktree.

Rebased onto `fa48d9de`. One conflict, in the `autoclose-merged` recurring
template: upstream removed `last_serviced_period:` (the serviced period is now
read from the repo-global log), my commit added a blackboard paragraph just
above it. Resolved by keeping both sides' intent — their removal, my paragraph.

## Adjacent, not fixed here

`append_report` exists as three byte-identical private copies in
`dream_validate_drift.py`, `dream_cleanup_orphan_markers.py`, and
`skill_update.py`. Rather than add a fourth, the shared one now lives in
`task_env.py` and those three are noted in its docstring. Collapsing them onto
it is a mechanical follow-up ticket — deliberately out of scope here.

## Notes for review

- The `## Dev` lines are read *during* the sweep, not after: they are the only
  trace of which checkout belongs to the ticket, and retire (or a task
  deletion) takes them away.
- The report is written only when something was stranded. It appends to a
  long-lived recurring task's blackboard, so a daily no-op line would grow that
  file without bound.
- The trailing Slack summary carries no owner mention — it is sweep-level, and
  the closed tickets may have different owners.
