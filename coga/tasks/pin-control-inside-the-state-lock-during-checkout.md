---
title: Pin control inside the state lock during checkout preparation
status: in_progress
owner: nicktoper
contexts:
- coga-dev/internals/git-refresh
- dev/checkouts/launch-boundary
- coga/state-publication
- coga-dev/internals/state-publication
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
agent: claude
---

## Description

`prepare_control_checkout` fetches and pins `origin/main` before taking `state_lock`, then reads local `main` inside the lock without re-pinning. A Coga publish that lands in between (push, then fast-forward of local `main`) makes local `main` look ahead of the stale pin. The realignment proof then runs against the stale pin and refuses with "local 'main' has commits not on origin/main (local Coga state commits are not yet on control: coga/log.md (lines not yet on control))", prescribing a `git pull --rebase` that was never needed. Fix it so a launch never refuses because control moved forward under it during preparation.

### Acceptance criteria

- [x] Local control moving forward to a commit already on the remote, between the fetch and the plan in `prepare_control_checkout`, no longer produces an `unpublished` (or any) refusal. Either the pin and the read of local control happen under the same `state_lock`, or a not-an-ancestor result re-fetches once inside the lock and re-plans before refusing.
- [x] The pre-mutation re-observation (`again = _plan_preparation(...)`) is checked against a pin that is current for the same lock hold. A pin that moved meanwhile re-plans; it does not apply a stale plan.
- [x] Genuine refusals are unchanged: a local hand commit of Coga state not on control still refuses `unpublished`, and a foreign commit still refuses `foreign`.
- [x] Regression test in `tests/test_git.py` (real Git, `git_repo` fixture): pin control, then publish a log line from the same checkout (or update-ref local control to a new remote commit) before `_plan_preparation` runs, and assert that preparation succeeds and lands on the new commit. A hook or monkeypatch on `_fetch_control`/`state_lock` entry may inject the interleaving deterministically.
- [x] Audit the other pin-then-lock readers of local control (`fast_forward_control` callers in `publish` and `refresh`, `git.py:467-560`) for the same window, and fix or explicitly rule out each one on the blackboard.
- [x] If behavior or wording changes, update `docs/contexts/dev/checkouts/launch-boundary/SKILL.md` step 2 ("Pins control") and its packaged twin, and/or the local-only `docs/contexts/coga-dev/internals/git-refresh/SKILL.md`; `tests/test_packaging.py` passes.

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

pr: https://github.com/FastJVM/coga/pull/1076
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

Completed 2026-10-21: Codex directly reviewed final head `8c3d0105dde810a86b826183e62ac3f72f32c71f`
against base `eacb72c97ac616d727853d597a3ec9692487f56e`. No nested reviewer CLI ran.
The initial review was independent of Claude's implementation; Codex then
implemented the human-approved review fix and completed a self-review of the
final diff. No independent review of that follow-up fix is claimed.
There are no unresolved must-fix findings.
Pushed `fix/prep-pin-under-state-lock` at `8c3d0105d` with an explicit
lease. The final presentation rendered successfully with all six diff paths
covered, current receipts, and no publication evidence gaps.

- **Resolved P2:** a sibling push followed by its delayed local-control
  fast-forward could cause a false evidence-change refusal. The loop now
  retries within the existing bound only when local control advances to a
  commit contained in the pin and all other evidence matches. HEAD may follow
  that move only when control is checked out. It builds and re-observes a new
  plan before mutation. Changed files, staging, branch, feature HEAD, or
  realignment evidence still refuse. The exhausted-retry diagnostic now names
  control refs, since either local or remote-tracking control may be moving.
- Reproduction and regression evidence: the initial independent review on
  `d9c0753a97ee06c92114a5ec13a8a034adacc6b2` / base
  `00b22b5e148a186ab98a66956f5b85302644260a` reproduced the false refusal
  using `.venv/bin/python /tmp/coga-pin-peer-probe.py`. After the clean
  rebase to `5a9c6d41c7264431cb08e6bfb1bdb036897613a6` / base `eacb72c97ac616d727853d597a3ec9692487f56e`,
  the new focused tests first reported 3 failed / 3 passed before the code fix.
  The final seven-case focused run passed before committing those changes as
  `8c3d0105d`; all seven are included in the committed-tree suite below.
- `.venv/bin/python -m pytest` on the final head/base: **3948 passed, 7 skipped
  in 425.80s**, Python 3.12.12, including `tests/test_packaging.py`. No Python
  3.11 run was performed. The initial review's 3941/7 result was historical.
- Both standalone real-Git probes were rerun on the final head/base: the split
  push/local-move reproduction now prepares on its first call; a same-checkout
  publication on lock entry prepares with fetch inside the lock; `refresh`
  succeeds when published control advances past its pin. Exact commands and
  receipts are in `## PR`.
- Final reconciliation: the unconditional rebase included current main at
  `eacb72c97ac616d727853d597a3ec9692487f56e`. Later main commits through `30d006850` changed only
  unrelated recurring tickets and the log. `check_branch_contains_control`
  returned `ok=True`, `state-only-drift`; no implementation or governing
  contract drift remains. The actual review base is still `eacb72c97ac616d727853d597a3ec9692487f56e`.
- No terminal, pager, TTY prompt, or rendered-message behavior changed; an
  interactive surface check is inapplicable. The remaining final-check/apply
  race and the possible dirty published files are disclosed in `## PR`.

## PR

```yaml
title: Re-pin control when it moves during checkout preparation
author: claude/codex
author_evidence: Claude authored the initial implementation in attended launch ebccd116-f981-405d-bf57-577b082b032d
  (claude-opus-5-5). Codex authored review fix 8c3d0105d after the human approved it on 2026-10-21.
head: 8c3d0105dde810a86b826183e62ac3f72f32c71f
base: eacb72c97ac616d727853d597a3ec9692487f56e
depth: deep
rationale: Inspect the Git checkout cleanup and concurrent shared-ref behavior. The final diff has passed
  the full suite and direct review, but the follow-up review fix was self-reviewed; the final-check/apply
  race remains explicit.
implementation: Fetch, pin and both preparation observations share one state_lock hold. A changed tracking
  ref re-pins and re-plans within three attempts. The same bound retries a delayed local-control fast-forward
  already contained in the pin when all other evidence matches, including HEAD following control only
  when checked out. fast_forward_control treats local control already past its requested commit and contained
  in the tracking ref as level.
deviations: The approved peer-review fix also handles a sibling push and local fast-forward arriving separately.
  Tracking-ref movement is checked locally without another fetch. No change to unpublished or foreign-commit
  refusals.
limitations: A sibling move after the final check and before apply is not retried; the guarded ref update
  or post-apply verification reports failed. The fast_forward_control shortcut can leave just-published
  files dirty for the next sweep. Verification used Python 3.12.12, not Python 3.11. No interactive surface
  changed.
files:
  src/coga/git.py: Pin inside the state lock, retry moved tracking refs and otherwise unchanged published
    local-control advances, and avoid stale fast_forward_control refusals.
  tests/test_git.py: Real-Git regressions for both pin observations, delayed local advances from feature/control,
    unchanged refusal behavior for other evidence changes, retry bounds, and the shared fast-forward shortcut.
  docs/contexts/coga/internals/git-refresh/SKILL.md: Describe the shared fast-forward level case and both
    bounded preparation retries.
  docs/contexts/dev/checkouts/launch-boundary/SKILL.md: Describe locked pinning, published local-control
    progress, and the remaining evidence refusal rule.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/git-refresh/SKILL.md: Packaged twin
    of the updated git-refresh contract, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkouts/launch-boundary/SKILL.md: Packaged
    twin of the updated launch-boundary contract, byte-identical.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 8c3d0105dde810a86b826183e62ac3f72f32c71f
  base: eacb72c97ac616d727853d597a3ec9692487f56e
  detail: Direct review completed on the final diff with no unresolved must-fix findings. The earlier
    independent Codex review of Claude implementation found one P2; Codex implemented its approved fix
    and completed final self-review. No independent review of the follow-up fix or nested reviewer CLI
    is claimed.
checks:
- command: .venv/bin/python -m pytest
  status: passed
  head: 8c3d0105dde810a86b826183e62ac3f72f32c71f
  base: eacb72c97ac616d727853d597a3ec9692487f56e
  detail: '3948 passed, 7 skipped in 425.80s on Python 3.12.12, including all seven new regression cases
    and packaging twin checks. Log: /tmp/coga-pin-peer-final-pytest.log.'
- command: .venv/bin/python /tmp/coga-pin-peer-probe.py && .venv/bin/python /tmp/coga-pin-peer-entry-probe.py
    && git diff --check
  status: passed
  head: 8c3d0105dde810a86b826183e62ac3f72f32c71f
  base: eacb72c97ac616d727853d597a3ec9692487f56e
  detail: 'Real-Git probes passed: the split push/local-ref move prepares immediately; publication on
    lock entry prepares with fetch inside the lock; refresh succeeds after published control advances.
    Diff whitespace check passed.'
- command: '.venv/bin/python - <<''PY''

    from pathlib import Path

    from coga.github_preflight import check_branch_contains_control

    root = Path.cwd()

    result = check_branch_contains_control(''origin'', ''main'', cwd=root, coga_root=root / ''coga'')

    print(result)

    assert result.ok, result.detail

    PY'
  status: passed
  head: 8c3d0105dde810a86b826183e62ac3f72f32c71f
  base: eacb72c97ac616d727853d597a3ec9692487f56e
  detail: ok=True, state-only-drift. Main advanced only through non-overlapping recurring tickets and
    log changes through 30d006850; the branch is safe to publish.
```
