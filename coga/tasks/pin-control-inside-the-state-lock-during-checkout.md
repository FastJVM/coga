---
title: Pin control inside the state lock during checkout preparation
status: in_progress
owner: nicktoper
contexts:
- coga/internals/git-refresh
- dev/checkouts/launch-boundary
- coga/internals/state-publication
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

`prepare_control_checkout` fetches and pins `origin/main` before taking `state_lock`, then reads local `main` inside the lock without re-pinning. A Coga publish that lands in between (push, then fast-forward of local `main`) makes local `main` look ahead of the stale pin. The realignment proof then runs against the stale pin and refuses with "local 'main' has commits not on origin/main (local Coga state commits are not yet on control: coga/log.md (lines not yet on control))", prescribing a `git pull --rebase` that was never needed. Fix it so a launch never refuses because control moved forward under it during preparation.

### Acceptance criteria

- [ ] Local control moving forward to a commit already on the remote, between the fetch and the plan in `prepare_control_checkout`, no longer produces an `unpublished` (or any) refusal. Either the pin and the read of local control happen under the same `state_lock`, or a not-an-ancestor result re-fetches once inside the lock and re-plans before refusing.
- [ ] The pre-mutation re-observation (`again = _plan_preparation(...)`) is checked against a pin that is current for the same lock hold. A pin that moved meanwhile re-plans; it does not apply a stale plan.
- [ ] Genuine refusals are unchanged: a local hand commit of Coga state not on control still refuses `unpublished`, and a foreign commit still refuses `foreign`.
- [ ] Regression test in `tests/test_git.py` (real Git, `git_repo` fixture): pin control, then publish a log line from the same checkout (or update-ref local control to a new remote commit) before `_plan_preparation` runs, and assert that preparation succeeds and lands on the new commit. A hook or monkeypatch on `_fetch_control`/`state_lock` entry may inject the interleaving deterministically.
- [ ] Audit the other pin-then-lock readers of local control (`fast_forward_control` callers in `publish` and `refresh`, `git.py:467-560`) for the same window, and fix or explicitly rule out each one on the blackboard.
- [ ] If behavior or wording changes, update `docs/contexts/dev/checkouts/launch-boundary/SKILL.md` step 2 ("Pins control") and/or `docs/contexts/coga/internals/git-refresh/SKILL.md`, plus their packaged twins under `src/coga/resources/templates/coga/bootstrap/contexts/`; `tests/test_packaging.py` passes.

## Context

Observed 2026-10-16 in the Multiply repo (`~/Code/codex/multiply`), on Coga at `d91574dd7`. `coga launch v0/live-codex-docker-smoke-test --agent codex` refused with the message above, naming only `main` and `coga/log.md (lines not yet on control)`. Evidence that it was a stale pin rather than a real unpublished commit:

- The `main` reflog shows only `merge <sha>: Fast-forward` entries, each one second after the matching `origin/main` "update by push". Local `main` never held a commit that `origin` lacked.
- The only commit that could have been flagged was `de64c5f3 Log: bootstrap/orient`. It adds one `coga/log.md` line: the launch record of a `coga chat` started in the same checkout at about the same moment. It was committed at 10:44:38, then pushed and fast-forwarded at 10:44:39. The prior pin would have been `7119d775`.
- Right afterwards `git fetch` showed `main...origin/main` level and the tree clean; a plain retry was all that was needed.

Mechanism in `src/coga/git.py`. `prepare_control_checkout` calls `_fetch_control` and `rev-parse refs/remotes/<remote>/<control>` to set `pinned` (around lines 1211-1219) **before** `with state_lock(cfg)`. `_plan_preparation` then reads `local = rev-parse refs/heads/<control>` inside the lock (around line 1269) and calls `_local_control_subsumed(local, pinned)`. A publisher holding the lock in that window pushes, advances `refs/remotes/<remote>/<control>`, and fast-forwards `refs/heads/<control>`. The waiter then compares a fresh `local` with its stale `pinned`. `state_lock` is per checkout, but sibling worktrees share `refs/heads/<control>`, and `fast_forward_control` moves it for them too. So a publish from another worktree can open the same window, not only a concurrent process in this checkout.

Relation to `launch-locks/checkout-exclusivity-lock` (in progress): that lock would stop a `coga chat` and a ticket launch overlapping in one checkout, which removes the trigger seen here. It does not cover a sibling worktree publishing and moving the shared control ref, and preparation should not depend on it, so this fix stands on its own. The `code/implement` step may cite that ticket but should not wait for it.

Related history: `recover-when-local-main-carries-hand-commits-of-co` (done) introduced the realignment proof; `stop-publish-union-merges-from-re-adding-log-lines` (done) shaped `_published_proof`'s union rule.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: fix/prep-pin-under-state-lock

## Plan (agreed with human 2026-10-20)

- `prepare_control_checkout`: fetch + pin + plan inside one `state_lock` hold; re-read the remote-tracking ref after the plan and after the re-observation, re-pin and re-plan (bounded attempts) when it moved. Covers sibling worktrees, whose pushes update the shared tracking ref.
- `fast_forward_control`: when local control already contains `new` and is contained in the current tracking ref, it is level — return True instead of a false realign refusal (covers `publish` and lock-free `refresh`).

## Handoff (implement, 2026-10-20)

Pushed `fix/prep-pin-under-state-lock` @ 4e324fdeb, rebased on origin/main 495debcbc.

What changed:
- `git.prepare_control_checkout`: `_fetch_control`, the pin and both `_plan_preparation` calls now run inside one `state_lock` hold. After the plan and again after the re-observation, `git._moved_pin` re-reads `refs/remotes/<remote>/<control>`; if it moved, re-pin and re-plan (bounded by `git.PREPARATION_ATTEMPTS = 3`, then refuse with "kept moving; retry"). A stale plan is never applied, and a refusal decided against a stale pin is never returned. Genuine refusals pay no extra fetch (the tracking ref is unchanged).
- Why both the lock and the re-read: `state_lock` is per checkout, but sibling worktrees share `refs/heads/<control>` and the tracking ref. A sibling publish (its push updates the shared tracking ref, and its fast-forward moves local control) is caught only by the re-read.
- `git.fast_forward_control`: when local is not an ancestor of `new`, but `new` is an ancestor of local and local is on the tracking ref (`git._published_control`), return True (already level) instead of `_realign_control` giving a false `unpublished`.
- Docs: launch-boundary step 2 and git-refresh (`fast_forward_control` and `prepare_control_checkout` bullets), plus their bootstrap twins (byte-identical).

Audit of other pin-then-read paths:
- `_publish_locked` → `fast_forward_control(new)`: base, fetch and push all run under this checkout's lock, but a sibling can publish past `new` before the local read → false realign note (the return value is ignored with a remote). Fixed by the shortcut. In the no-remote branch, local can't get ahead of `new` (siblings build on local control only after our move), so it's unaffected.
- `refresh`: takes no lock; fetch → rev-parse → `fast_forward_control` has the same window, and a false False made recurring exit 75. Fixed by the same shortcut.
- The "already on control" `fast_forward_control(base)` in publish: same shortcut applies.
- Remaining gap (accepted): a sibling move between the last `_moved_pin` and `_apply_preparation`. The guarded `update-ref` (realign) or the post-apply verify reports `failed`; it is never silent.

Tests (`tests/test_git.py`):
- `test_prepare_repins_when_control_moves_under_it[plan|re-observation]`
- `test_prepare_refuses_when_control_keeps_moving`
- `test_fast_forward_treats_control_already_moved_past_new_as_level`
- Before the fix, with the git.py change stashed, all 4 failed. The repin cases reproduced the reported `unpublished` coga/log.md refusal.
- Genuine refusals stay covered by the existing `test_prepare_refuses_an_ahead_or_diverged_control_and_changes_nothing` (foreign), `test_prepare_names_the_rebase_for_an_unpublished_hand_commit_and_retry_recovers` (unpublished), `test_fast_forward_leaves_an_ahead_main_alone_and_names_the_fix`, and `test_refresh_refuses_an_ahead_or_diverged_control_checkout`. All pass.

Env note: the shell's `python` lacks tomlkit; tests run with `.venv/bin/python -m pytest`.


## Peer review

Codex direct review, 2026-10-20. Review of the implementation completed on
`d9c0753a97ee06c92114a5ec13a8a034adacc6b2` against
`00b22b5e148a186ab98a66956f5b85302644260a` after a clean rebase. This is an
independent review of Claude's implementation; no nested reviewer CLI ran.
One must-fix finding remains; the attending human has been asked before code
changes, per Session conduct. The full suite passed: `.venv/bin/python -m pytest`
reported **3941 passed, 7 skipped in 353.63s** on Python 3.12.12, including
the packaging twin checks. No claim of a Python 3.11 run. The rebased branch
was pushed with an explicit lease; `git range-diff` confirms its implementation
patch is unchanged. No workflow transition has been run.

- **P2 — retry a published local-control advance between observations.** A
  sibling's push updates the tracking ref before its later local-control
  fast-forward. If the first planning pass observes the push, the loop
  re-pins; if the sibling then advances local control between the next two
  planning passes, the tracking ref is already stable. The evidence mismatch
  returns `refused: the checkout changed while it was being examined; retry`
  even though local control equals remote control and the checkout is clean.
  This happens before the final pin check/apply gap already disclosed in the
  implement handoff. Reproduced using real Git with
  `.venv/bin/python /tmp/coga-pin-peer-probe.py`: first pass pushes/fetches a
  log-line commit, second pass advances local main to it after recording its
  plan, third pass observes the new local main and refuses. An immediate
  ordinary retry prepares successfully. Proposed fix: retry within the same
  bound when only a proven published forward move of local control changed
  the evidence; preserve unrelated evidence-change and unpublished/foreign
  refusal behavior. Confirmation pending.
- Additional real-Git probes passed:
  `.venv/bin/python /tmp/coga-pin-peer-entry-probe.py` verifies a same-checkout
  log publication on lock entry (including asserting preparation's fetch
  occurs inside the lock) and `refresh` when control advances past its pin.
- No interactive terminal, pager, or rendered-message surface changes in this
  diff; the review concerns Git/state behavior and plain diagnostics.

## PR

```yaml
title: Re-pin control when it moves under checkout preparation
author: claude
author_evidence: Implement session ran as Claude Code on claude-opus-5-5 (attended launch ebccd116-f981-405d-bf57-577b082b032d).
head: d9c0753a97ee06c92114a5ec13a8a034adacc6b2
base: 00b22b5e148a186ab98a66956f5b85302644260a
depth: deep
rationale: Direct review found an unresolved false refusal when a sibling advances local control after its push has already been re-pinned. Git checkout mutation and concurrency behavior warrant inspection; implementation approval for the review fix is pending.
implementation: Fetch, pin and plan share one state_lock hold; a remote-tracking ref that moved past the pin re-pins and re-plans (bounded). fast_forward_control treats local control that already contains new and is on the tracking ref as level.
deviations: None from the ticket. Re-reads the tracking ref (no network) instead of re-fetching, since every in-repo move of local control also moves the shared tracking ref.
limitations: A sibling push followed by a delayed local-control advance between observations still produces a false refusal (see Peer review). The previously disclosed final re-check/apply race reports failed; the shortcut may leave just-published files dirty for the next sweep.
files:
  src/coga/git.py: Re-pin loop in prepare_control_checkout, _moved_pin, _published_control, fast_forward_control shortcut, PREPARATION_ATTEMPTS.
  tests/test_git.py: Regression tests for a moved pin at plan and re-observation, the bounded refusal, and the fast_forward_control shortcut.
  docs/contexts/dev/checkouts/launch-boundary/SKILL.md: Step 2 states the pin is taken under the lock and re-pinned when control moves.
  docs/contexts/coga/internals/git-refresh/SKILL.md: Documents the fast_forward_control level case and the re-pin in prepare_control_checkout.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkouts/launch-boundary/SKILL.md: Packaged twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/git-refresh/SKILL.md: Packaged twin, byte-identical.
review:
  reviewer: codex
  kind: independent
  status: failed
  head: d9c0753a97ee06c92114a5ec13a8a034adacc6b2
  base: 00b22b5e148a186ab98a66956f5b85302644260a
  detail: Direct review completed with one unresolved P2 false-refusal finding, reproduced in a real-Git probe. The original same-checkout race and the refresh shortcut passed additional probes. No interactive surface changed.
checks:
  - command: .venv/bin/python -m pytest
    status: passed
    head: d9c0753a97ee06c92114a5ec13a8a034adacc6b2
    base: 00b22b5e148a186ab98a66956f5b85302644260a
    detail: 3941 passed, 7 skipped in 353.63s on Python 3.12.12 after the clean rebase, including packaging twins; no Python 3.11 run. Log at /tmp/coga-pin-peer-review-pytest.log.
  - command: .venv/bin/python /tmp/coga-pin-peer-probe.py
    status: failed
    head: d9c0753a97ee06c92114a5ec13a8a034adacc6b2
    base: 00b22b5e148a186ab98a66956f5b85302644260a
    detail: Real-Git interleaving still refuses a clean checkout with local main equal to the remote; an ordinary retry succeeds.
  - command: .venv/bin/python /tmp/coga-pin-peer-entry-probe.py
    status: passed
    head: d9c0753a97ee06c92114a5ec13a8a034adacc6b2
    base: 00b22b5e148a186ab98a66956f5b85302644260a
    detail: Preparation fetch occurs under the lock and succeeds after a same-checkout publish on lock entry; refresh succeeds when published control advances past its pin.
  - command: .venv/bin/python -m pytest
    status: passed
    head: 4e324fdeb45d9b8c74f91546355f991e3bb805f8
    base: 495debcbcaecf142bf783b344572be6b3d06703c
    detail: 3941 passed, 7 skipped in 326.70s (committed tree, after rebase).
```
