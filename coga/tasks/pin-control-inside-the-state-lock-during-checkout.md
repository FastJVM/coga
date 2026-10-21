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
step: 1 (implement)
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
