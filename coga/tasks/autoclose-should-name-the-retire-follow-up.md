---
slug: autoclose-should-name-the-retire-follow-up
title: Autoclose should name the retire follow-up
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/694
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

Implementation commit `d5544542` on `autoclose-retire-hint`, followed by peer
review commit `672236e3`.

- `src/coga/autoclose.py`: `ClosedTicket` / `AutocloseResult`, `sweep_merged`
  returns the latter, `_try_bump_one` reads the blackboard once and returns the
  closed ticket, `render_retire_report` / `render_retire_summary` /
  `_report_retire_followups`, wired into `run_autoclose_recipe`.
- `src/coga/autoclose.py`: a recipe-local atomic report append built on the
  shared task blackboard CAS primitive; `task_env.blackboard_from_env` still
  resolves *where* the recipe's report goes.
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

## Peer-review scope correction

`append_report` still exists as three byte-identical private copies in
`dream_validate_drift.py`, `dream_cleanup_orphan_markers.py`, and
`skill_update.py`. Peer review rejected moving a fourth single-consumer helper
into shared `task_env` infra while those real consumers remained unmigrated.
Autoclose therefore keeps its atomic append beside its recipe; consolidating
the older writers remains outside this ticket.

## Notes for review

- The `## Dev` lines are read *during* the sweep, not after: they are the only
  trace of which checkout belongs to the ticket, and retire (or a task
  deletion) takes them away.
- The report is written only when something was stranded. It appends to a
  long-lived recurring task's blackboard, so a daily no-op line would grow that
  file without bound.
- The trailing Slack summary carries no owner mention — it is sweep-level, and
  the closed tickets may have different owners.

## Peer review — design gate

`codex review --base main` completed cleanly on the retry. It found one P1
lifecycle conflict that needs an owner decision before implementation:

- The recurring sweep runs autoclose before Dream. Autoclose closes the source
  ticket and names `coga retire <slug>`, then Dream's current Phase 4 contract
  directly deletes every done ticket. That can delete both the source ticket's
  `## Dev` evidence and the period task holding the report in the same sweep.
  The advertised command then immediately fails to resolve the slug while the
  checkout debt remains.
- Recommended resolution: make done tickets with a recorded `branch:` or
  `worktree:` ineligible for Dream deletion. They remain deliberately visible
  until a human runs `coga retire`, whose existing safety checks and Retro path
  own checkout cleanup and ticket deletion. Tradeoff: Dream no longer deletes
  every done ticket immediately; checkout-bearing done tickets are retained as
  explicit operational debt.
- Rejected as broader alternatives: teach Dream to duplicate/drive retire's
  safety machinery, or recover already-deleted ticket evidence from git
  history. Both blur the intentionally human-typed retirement boundary.

The review also found implementation-level must-fixes to apply after that
decision: retain and report successful earlier closures when a later ticket
errors; preflight the live Slack summary before mutating tickets; give failed
summary delivery a durable task log; replace the whole-file report rewrite
with the atomic ticket blackboard primitive; and keep the new report helper at
its sole consumer rather than adding single-consumer code to core infra.

Owner approved the recommended Dream eligibility guard in the launch REPL.

## Peer review — fixes applied

- Dream now excludes any done ticket with a real `branch:` or `worktree:` under
  `## Dev`, leaves its evidence in place for the human-typed retire command,
  and records it as deferred retirement debt. Live and packaged Dream
  templates match; the recurring and current-direction contexts carry the
  durable rationale.
- The recipe owns its running `AutocloseResult`, so a later GitHub/validation
  failure still reports earlier committed closures. A failure after
  `mark_done` writes `done` is detected from both the mutated object and disk
  and reported before the original exception continues.
- Any live notification required by a candidate is preflighted before the
  terminal write. A transient summary delivery miss is nonfatal only after the
  report exists and is logged against the validated host task.
- Report append is local to `autoclose.py` and uses the atomic blackboard
  read/replace CAS primitive, preserving CRLF and refusing concurrent changes;
  the proposed single-consumer `task_env` helper is gone from the branch.

Focused verification: `python -m pytest tests/test_autoclose.py
tests/test_dream_worker_templates.py` — 55 passed. `git diff --check` clean;
all four changed live/packaged template pairs compare byte-identical.

## Final peer-review verification

- Committed review findings as `672236e3` after a full green run.
- Unconditionally fetched `origin/main` and rebased both feature commits onto
  `bcf82368`; the rebase completed without conflicts.
- Re-ran `python -m pytest` after the rebase: 1755 passed, 1 skipped.
- `git diff --check origin/main...HEAD` is clean; the feature worktree is clean,
  its merge base is exactly `origin/main`, and the branch has two commits ahead.
- `coga validate --json` reports 112 OK plus existing config/task issues only;
  every reported issue is in state outside this branch diff.

## PR

### Summary

- Capture checkout metadata while autoclose still has the source ticket, then
  report each exact `coga retire <slug>` follow-up on the run blackboard/stdout
  and in one trailing Slack summary without deleting anything.
- Preserve already-committed closures across later sweep failures, preflight
  required live notification configuration before mutation, append reports
  atomically, and durably log transient summary delivery failures.
- Keep checkout-bearing done tickets out of Dream so their slug and `## Dev`
  evidence remain available until a human runs the named retire command; keep
  the live and packaged contracts in sync.

### Test plan

`python -m pytest` (1755 passed, 1 skipped); `coga validate --json` (112 OK; only existing config/task issues outside this diff).
