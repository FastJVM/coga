---
title: stop using worktrees
status: in_progress
owner: nicktoper
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
step: 2 (peer-review)
agent: claude
---

## Description

Code-ticket work runs in the checkout the session was launched from. No
linked worktrees for ticket work. Every code step starts and ends on `main`:

1. **Start:** the checkout is on `main`, clean, and fast-forwarded to
   `origin/main`. Create the feature branch from there.
2. **Work:** implement and commit on the feature branch in the same checkout.
3. **End:** push the branch (and open/update the PR where the step does),
   then `git switch main` and fast-forward it to `origin/main`. The session
   leaves the checkout on `main`, clean.

If the checkout is dirty or on another ticket's branch at start, stop and ask
the human (attended) or block (unattended). Do not work around it with a
linked worktree or a control checkout.

**Exception kept:** the sandbox clone fallback (a `/tmp` clone when the
sandbox mounts `.git` read-only) stays as the only alternative checkout.

**Out of scope:** Coga-internal temporary worktrees used by recurring jobs
and Dream (`coga/internals/recurring-temp-worktrees`) stay as they are.

## Context

Today (2026-09-24) single checkout is already the documented default, but:

- `code/implement` still creates linked worktrees (`../coga-control`,
  `../coga-<branch>`) when the primary checkout is "occupied" (dirty or
  holding another live ticket's branch).
- In single-checkout mode the agent stays on the feature branch through
  `## Dev`, `coga bump`, and `coga open-pr`. Nothing returns the checkout
  to `main`, so the operator's repo is left on stale feature branches.

Likely touchpoints (check each; keep packaged twins byte-identical):

- Contracts: `docs/contexts/dev/checkouts`, `dev/code`, `dev/dev-record`
  (`worktree:` field: keep, drop, or make optional),
  `dev/checkout-cleanup`.
- Skills: `code/implement`, `code/open-pr`, `code/address-pr-comments`,
  `code/self-qa`, `direct/body`, plus twins under
  `src/coga/resources/templates/coga/bootstrap/skills/`.
- Core: `open_pr._checkout_mode` (publishing ticket state while on the
  feature branch versus after returning to `main`), `sync_coga_state` exit
  sweep, `retire` / `autoclose` / `checkout_disposal` worktree handling,
  `[git] worktrees_ticket_owned`.

## Decisions

Settled with the owner on 2026-09-24. Implement these; do not reopen them
without asking.

1. **Returning to `main` with dirty Coga state.** On a feature branch the exit
   sweep publishes `coga/tasks/**`, `coga/log.md`, and `coga/recurring/**` to
   `origin/main` but leaves the local copies dirty (`coga/sync`), and a stale
   local `main` can make `git switch main` refuse. The end-of-step procedure:
   fetch, verify each dirty Coga-state path matches `origin/main` byte for
   byte, discard those paths, `git switch main`, `git merge --ff-only
   origin/main`. If any dirty path is *not* already published, or any
   non-Coga path is dirty, stop and escalate. Never discard unpublished
   state.
2. **Start check is strict.** Because every session now leaves `main` clean,
   the start check requires HEAD on `main`, a clean tree (Coga state
   included), and a fast-forward to `origin/main`. Anything else means stop
   and ask (attended) or `coga block` (unattended).
3. **`open-pr` runs from `main` by branch name.** Reuse the existing
   control-checkout path that pushes the recorded branch by name without
   entering it. Remove the same-checkout-on-feature-branch path in
   `open_pr._checkout_mode` (and the `COGA_EXPECTED_TASK` ownership proof it
   exists for) unless the sandbox clone still needs part of it. Ticket state
   (`## Dev`, bump, log) is written on `main` and published by the normal
   sweep.
4. **Every step follows the rule.** Peer-review reads
   `git diff main...<branch>` without switching. Steps that change code
   (implement, review/`address-pr-comments`) switch to the branch, commit,
   push, and run the end-of-step procedure from decision 1.
5. **`worktree:` in `## Dev`.** Keep it only for the sandbox clone
   fallback. Otherwise record `branch:` alone. Keep the
   `retire`/`autoclose`/`checkout_disposal` worktree handling so existing
   linked worktrees on disk still get cleaned up.

Expected size: one PR, mostly deletion (the separate-worktree layout, the
occupied-checkout control-worktree procedure, the same-checkout open-pr
mode). If it grows past that, split per `code/split-ticket`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan (implement, 2026-09-24)

Owner-confirmed additions to the Decisions (attended session):

- **1a. Launch publishes its `launched` line before spawning** (`git.sync_log`),
  so the strict start check (decision 2) sees a genuinely clean tree.
- **2. Ticket state is written only while on `main`** — before creating /
  switching to the branch, or after returning. On the branch the agent edits
  code only; decision 1's escalation then catches only real anomalies.
- **3. `open_pr` gains a by-ref mode** for `branch:` without `worktree:`:
  runs in the primary checkout on `main`, counts `base..<branch>`, checks
  freshness against `<branch>` (`check_branch_contains_control(head=...)`),
  pushes `<remote> <branch>`. The sandbox-clone path (`worktree:` recorded)
  keeps today's in-checkout gate. The same-checkout-on-feature-branch mode and
  `COGA_EXPECTED_TASK` proof in `_checkout_mode` go.
- Implement now pushes its branch at end of step (ticket "End" rule).

This session runs under the old single-checkout rule (feature branch in this
checkout) because the new rule is what it implements.

## Dev
branch: stop-using-worktrees
worktree: /home/n/Code/coga

(This ticket ran under the old single-checkout rule: the installed `coga`
still requires `worktree:` and uses the same-checkout open-pr mode. The
branch is committed and rebased on origin/main, not pushed — the old
implement skill defers the push to open-pr.)

## Implementation notes (implement step)

Code:
- `commands/launch.py`: every ordinary launch passes `commit_log=True`, so the
  `launched` audit line publishes before the agent spawns (megalaunch's
  deferred audit already publishes with its launch admission).
- `step_gate.py`: `requires: branch` needs only `branch:`.
- `open_pr.py`: `_checkout_mode` is now "must be on control" only (no
  `COGA_EXPECTED_TASK` proof). New by-ref mode when no `worktree:` (or a
  `worktree:` naming this checkout, from the retired single-checkout layout):
  checks `refs/heads/<branch>` exists, `base..<branch>` ahead, freshness via
  `check_branch_contains_control(head=...)`, pushes by name. A recorded
  sandbox clone keeps the in-checkout gate (`_check_recorded_clone`).
  Deleted: `_single_checkout_publishable_paths` + helpers, `_sync_pr_record`,
  the `sync_log`/state-exclusion path.
- `github_preflight.check_branch_contains_control`: `head=` param; dropped
  `allow_identical_coga_state_overlaps` (single-checkout only).
- Comments: `repl_supervisor` (EXPECTED_TASK readers), `bump` advisory docstring.

Docs/skills (live + packaged twins): `dev/checkouts` (owner of the
start/work/end rule), `dev/dev-record`, `dev/code`, `dev/checkout-cleanup`,
`coga/internals/pr-publication`, `coga/internals/agent-spawn`,
`coga/session-conduct`; skills `code/implement`, `code/open-pr`,
`code/self-qa`, `code/address-pr-comments`, `coga/recurring/verify`; packaged
workflows `code/{with-review,with-self-review,design-then-implement}`,
`docs/with-review` (it also created linked worktrees); example fixture
`example/coga/workflows/code/with-review.md`.

Interpretation of decision 4: peer-review reads the diff by name from `main`,
then (it always rebases, and applies must-fix findings) switches to the
branch, commits, pushes with `--force-with-lease`, and returns. Self-QA is
treated as a code-changing step too.

Baseline before changes: 1 pre-existing failure,
`tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`
(`coga/recurring/phone-home/ticket.md` twin drift — recurring state, unrelated).

Follow-ups (not done here, scope):
- The recorded-checkout PR-assist machinery (`pr_assist.py`,
  `launch._recorded_single_checkout_assist_branch` / alignment,
  `coga/internals/human-assist`, `coga/internals/assist-publication`) is
  now reachable only when an assist is launched from a recorded sandbox clone
  on the branch. Candidate for removal in its own ticket.
- `coga/tasks/v2/use-worktree-when-starting-a-dev-task.md` proposes the
  opposite direction; the owner should cancel or rewrite it.
- `bump._warn_stranded_task_state` keeps its legacy single-checkout silence
  rule; harmless, could be dropped later.
