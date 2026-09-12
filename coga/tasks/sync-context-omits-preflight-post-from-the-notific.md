---
title: Sync context omits preflight_post from the notification contract
status: in_progress
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
step: 4 (review)
---

## Description

`coga/contexts/coga/sync/SKILL.md` explains at length why lifecycle broadcasts pass
`fatal=False` — the markdown is already written, so a delivery miss must not abort the
command or skip `emit_done_marker` — and asserts that "Misconfiguration (an unresolved
webhook) still crashes on both paths".

What it never says is *when* that crash happens, or that keeping it useful required a
separate mechanism: `notification.preflight_post`, whose own docstring is "Fail before a
state mutation when a selected live channel is unusable".

Without the preflight, a repo with an unresolved webhook would flip the ticket, write the
audit line, sync to the control branch, and only then die inside `SlackChannel` — the
exact half-applied outcome `fatal=False` exists to prevent, arriving through the
configuration branch instead of the delivery branch.

The context's "Design rule for new features" section is where an author is told what to
wire up when adding a state-changing command. It lists cadence, destination, the
post-after-write ordering, and `git.sync_task_state` — but not the preflight. So the next
such command will omit it, and **the omission is invisible in any repo whose webhook
resolves**.

Deliverable: document the preflight as the third element of the notification contract
alongside cadence and destination, naming its call sites and the `important=True` form.

## Context

Citations name symbols and files, not line numbers.

`notification.preflight_post(cfg, *, important=False)` calls `require_webhook` for every
enabled channel and is invoked at five independent call sites ahead of the mutation:

- `src/coga/commands/block.py`
- `src/coga/commands/bump.py`
- `src/coga/commands/mark.py`
- `src/coga/launch_script.py`
- `src/coga/autoclose.py`

Verify the list is still exactly five before writing — `grep -rn preflight_post src/coga/`
is the check.

Related but separate: Dream 2026-W36 opened a proposal PR correcting two other claims in
this same context (the live-producer module list, and the missing
`slack_response.py` classification and `redact_slack_webhook_credentials` boundary). Check
whether that PR has merged before starting, and rebase onto it rather than editing the same
section twice.

`coga/contexts/coga/sync/SKILL.md` is an enforced byte-identical twin with
`src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`
(`IDENTICAL_LIVE_PACKAGED_PAIRS` in `tests/test_packaging.py`) — edit both. It is 59 KB;
locate the target section with grep rather than reading it whole.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shard `ks-08`), classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/791
branch: sync-context-preflight
worktree: /home/n/Code/claude/coga-sync-context-preflight

## Findings (implement)

- Dream PR #738 (live-producer list, `slack_response.py` boundary) and #767 have
  both merged; no rebase conflict. Live and packaged `coga/sync` twins were
  byte-identical at start and remain so after the edit.
- The ticket's call-site list is stale. `grep -rn preflight_post src/coga/`
  finds **seven call sites in six modules**: the five listed plus
  `commands/launch.py::_launch` twice (script-assist setup path; before assist
  lifecycle state is published on a non-`in_progress` ticket). Documented all
  seven, not five.
- No caller passes `important=True`. Existing important alerts handle failure
  after the write: script failure, scan summaries, and watchdog outcomes use
  `fatal=False`; `mark.py::_warn_if_state_not_advanced` instead uses the default
  `fatal=True` inside its advisory exception guard (corrected at peer review).
  Documented the form and stated plainly that it has no consumer today.

## Changes

`coga/contexts/coga/sync/SKILL.md` (+ packaged twin), three edits:
1. "Design rule for new features": first paragraph rewritten as a numbered
   three-element contract — surface, destination, preflight — with the rule
   that a `fatal=False` producer calls `preflight_post(cfg)` before its write,
   gated like `bump` on whether the invocation will actually post live.
2. "Notification implementation pointers": new `preflight_post` bullet after
   the `post` bullet naming the seven call sites with enclosing functions and
   gating conditions, the assist `_bail` vs re-raise split, and the
   `important=True` form.
3. Fail-loud section: the "`commands/*` module runs it" aside now points at the
   caller inventory and distinguishes refusal before mutation from reporting
   and dropping a failed announcement after mutation.

Tests: full suite 2435 passed (`.venv/bin/python -m pytest`); packaging twin
test green. No code change, no fixture change needed.

## Adjacent finding (not fixed here)

Existing important alerts do not preflight the important route, so a repo with
`webhook` set but `important_webhook` unset loses the alert with a stderr
diagnostic. Script failures, scan summaries, and watchdog outcomes use
`fatal=False`; the stale-period warning catches failures in its own advisory
guard. Whether per-ticket script-failure alerts should preflight
`important=True` is a design question outside this documentation fix. No
follow-up ticket exists.

## Peer review

- `codex review --base main` **returned** from the recorded feature worktree
  at `c8e21145`, with one P2 finding: the new prose incorrectly claimed an
  unresolved webhook crashes after a non-fatal post. Corrected both repeated
  explanations in both context twins: `fatal=False` reports and drops; the
  preflight preserves refusal before mutation.
- Source inspection confirmed seven calls in six modules and no
  `important=True` consumer. Also narrowed the universal preflight claim to
  the actual caller conditions and corrected the stale-period warning's
  advisory guard and the script phase's `ScriptPublicationError` handoff.
- GitHub confirms Dream PRs #738 and #767 are merged. The review's 69 focused
  checks passed; its wheel-build check lacked `hatchling` in the default
  interpreter. The full suite with the repository `.venv` passed all 2435
  tests, including the wheel build (`/home/n/Code/claude/coga/.venv/bin/python
  -m pytest`, run from the feature worktree).
- Committed the corrections, fetched `origin main`, and rebased onto
  `d7a263ec` without conflicts. The context bytes are unchanged by the rebase,
  and both twins remain byte-identical. The branch is clean at `ab4d2b8e`,
  with two commits ahead of `main`; `git diff --check main...HEAD` passes.
  The required full-suite run after rebase also passed: **2435 passed** in
  171.86s with the same command. No must-fix findings remain.

## PR

Document `notification.preflight_post` as the third element of the sync
context's notification contract, alongside surface and destination. Name all
seven call sites in six modules, their admission conditions, and the
`important=True` form, which has no current caller.

Clarify that preflight refuses an unresolved webhook before mutation, while
`fatal=False` reports and drops failures after the write so the command can
finish. Update the live context and its packaged twin together.

Test plan: `/home/n/Code/claude/coga/.venv/bin/python -m pytest` from the feature worktree — 2435 passed after rebase; `git diff --check main...HEAD` passed.
