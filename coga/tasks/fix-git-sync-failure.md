---
title: fix git sync failure
status: draft
owner: nicktoper
workflow: code/with-self-review
---

## Description

A launch teardown on the control branch fails its state refresh whenever the
local control branch has unpushed coga-state commits and the remote has moved:

```
[git] refresh failed: `git merge --ff-only --quiet a35975c…` failed (exit 128):
fatal: Not possible to fast-forward, aborting.. Message was: Refresh coga state after launch
```

The unpushed commits are coga's own doing: the publish half of sync is
local-first, so when a transition runs offline (in `multiply`: `git fetch …
Could not resolve host: github.com`) it commits `coga/log.md` / task state
locally and the push fails. Nothing reconciles that afterwards — the refresh
half only knows `merge --ff-only` on the control branch — so every later
launch ends with the message above until some unrelated transition happens to
push. The same line appears in `multiply`'s log on 2026-09-09 and 2026-09-18;
it recurs in other repos too.

Make the control-branch refresh reconcile a local-ahead or diverged control
branch the same way the publish half already does: fetch; if local is merely
behind or already current, keep the existing `merge --ff-only` (no stash, no
push); only when local is ahead or diverged, rebase the local control commits
onto the fetched tip (`coga/log.md` union-merges, task files are coga state)
and push them. A refresh that ends with local control matching
`origin/<control>` is the definition of done. A genuine conflict (product
files diverged on `main`) stays a loud non-fatal miss, and the message must
name the recovery: `git pull --rebase origin <control> && git push`. A rebase
that succeeds but whose push fails on transport is also a miss (return
False, log it) — the local branch is left rebased, which is strictly better
than before, and the next transition's push will publish it.

The same unreconciled divergence also breaks `coga megalaunch`, because its
strict claim/activation publisher requires local `HEAD` to *be* the fetched
control tip. Observed 2026-09-18 17:17 in this repo, three picks refused in one
run:

```
launch claim publication refused: checked-out control branch moved from
verified tip 3cc8082… to 578c49c… before strict state publication; retry
```

Local `main` had sat at a 12:42 tip; another clone pushed four lifecycle
commits at 17:13; the launch teardown at 17:15 committed its `Log:` line on the
stale tip without reconciling — `main` ahead 1 / behind 4, the `multiply`
shape. The strict path was right to refuse a diverged base; the defect is that
refresh let the branch get there. Ten seconds later the next launch's publish
half rebased and pushed, and `main == origin/main` again. The refresh fix above
is what prevents this; the definition of done includes megalaunch admitting a
pick right after a launch teardown in a checkout whose remote moved meanwhile.

## Context

- Refresh entry point: `git.refresh_coga_state_from_control`. The
  control-branch case is the short block `if branch == cfg.git_control_branch:
  _run_git(root, "merge", "--ff-only", "--quiet", tip); return True` right
  after `_fetch_branch_oid`. Everything else in that function is the
  feature-branch overlay and assist-publication path — leave it alone. Its
  docstring ("a diverged local control is a loud non-fatal miss, never an
  implicit merge") restates the old contract; rewrite it in the same PR.
- Decide ahead/behind with `git merge-base --is-ancestor HEAD <tip>` (behind
  or current → ff-only as today) before falling into rebase+push. Do not
  route every refresh through `_rebase_onto_remote`: it calls
  `_stash_if_dirty` unconditionally, and a stash push/pop on every dirty
  teardown is exactly the surface that produced the orphaned stashes below.
- Push scope: `_push_control_branch` pushes the whole branch, not only coga
  state. An operator's deliberate local-only product commits on `main` would
  be published by a launch teardown. The publish half already behaves this
  way on every transition, so this is consistent, not new — but say so in
  the docstring.
- Two callers (`grep -n refresh_coga_state_from_control src/coga`):
  `launch._refresh_launch_checkout` (teardown — the case this ticket is
  about) and the recurring pre-launch verification in `launch.py` that passes
  `require_control_verification=True` and is framed as "no work was started"
  on bail. With this change that call can push a prior offline child's
  unpushed commits before admission. That is the intended behavior (flushing
  stranded state is what verification should do); document it at that call
  site rather than special-casing it.
- The publish half already solves this: `git._push_control_branch` pushes, and
  on a non-fast-forward reject calls `git._rebase_onto_remote` (fetch, explicit
  stash-if-dirty, `git rebase <tip>`, restore-to-orig on any failure, pop
  stash), bounded by `_MAX_SYNC_ATTEMPTS`. The fix is to reuse that pair from
  the refresh path rather than write a third integrate-remote-control routine.
  The relationship that matters: refresh and publish are the same operation on
  the control branch ("make local control == remote control, keeping local
  commits"), so they must not have different behavior.
- Local-first commit contract: `git._sync_paths_on_control_branch` commits
  before pushing and only unwinds the commit on a `StateRegressionError`, not
  on a transport failure. That is intentional (state survives offline) and is
  what leaves the unpushed commits behind; do not change it here.
- Reproduction to encode as a test in `tests/test_git.py` (the existing
  control-branch case is `test_refresh_fast_forwards_control_branch_checkout`,
  whose docstring also restates the ff-only contract and must be updated; the
  `git_repo` fixture gives a checkout plus bare remote): commit coga state
  on local `main` without pushing, advance the remote `main` independently
  (a product-file commit), run `refresh_coga_state_from_control`, assert it
  returns True, `main == origin/main`, both sides' commits present, no stash
  left behind, and no `refresh failed` line in `coga/log.md`. Add the
  conflict case too: a diverged product file must leave the tree clean, the
  local commits intact, and print a recovery hint.
- Live repro was `~/Code/multiply` (`main` ahead 2 / behind 9). It was hand-
  repaired during ticket authoring with `git pull --rebase origin main && git
  push` — the rebase union-merged `coga/log.md` cleanly, which is the evidence
  the automatic path is safe. That repo also carries two orphaned coga stashes
  (`coga log.md launch line (session b8b9626f)` from 2026-09-09, and a
  `coga open-pr borrow` one) — a second symptom of the stash-based sync
  leaving state behind. Out of scope here; it is an input to
  `simplify-git-sync`.
- Contexts cited, not attached (the work depends on one sentence and one
  test command, not on rules spread across either file): `coga/sync`
  (`coga/contexts/coga/sync/SKILL.md`, `### The launch-end pull-back —
  refresh_coga_state_from_control` inside `## Git — durable task-state sync`,
  the "on the control branch that is a plain `merge --ff-only`" sentence —
  update it in the same PR, plus the packaged twin under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`,
  which `tests/test_packaging.py` requires to stay byte-identical);
  `coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`, test expectations:
  `python -m pytest tests/test_git.py`).
- Strict publish entry point, for the megalaunch symptom:
  `git._sync_paths_on_control_branch_strict` (`src/coga/git.py`, the
  `control_tip = _control_base_for_attempt(…, 1)` /
  `if current_oid != control_tip: raise GitError(…)` block). Megalaunch
  reaches it through `mark_in_progress(strict_state_sync=True)` for claim
  writes and through the activation flip, so both the prefixed
  `launch claim publication refused: …` outcome and the bare
  `checked-out control branch moved …` outcome are this one check. Leave the
  refusal of a diverged or behind `HEAD` alone — that is the CAS working, and
  the refresh fix removes the state that trips it. One residual worth closing
  in the same change, cheap: a `HEAD` strictly *ahead* of the fetched tip by
  Coga's own unpushed commits (a sibling launch in the same checkout whose
  push is in flight) is also refused today; relax the equality to
  `git merge-base --is-ancestor <control_tip> HEAD`, commit on `HEAD` exactly
  as now, and keep the existing `--force-with-lease=refs/heads/<control>:
  <control_tip>` push — the lease still rejects a genuine remote move and
  `_restore_strict_state_commit` still unwinds only the one generated commit.
  Do not add a rebase to the strict path.
- Strict-path tests for `tests/test_git.py` (there are none; the only
  `moved from verified tip` test is the feature-branch CAS): (a) the ahead
  case — commit a `coga/log.md` line on local `main` without pushing, call
  `sync_task_state(…, strict_state_sync=True)` with a `ticket_state_guard`,
  assert success, the generated commit's parent is the unpushed local commit,
  `origin/main` carries both, `main == origin/main`; (b) the diverged case —
  advance the remote independently and assert the existing `GitError` still
  fires with the tree and local commits intact; (c) the end-to-end shape from
  the description — refresh after a launch with a moved remote, then a strict
  publish succeeds without any intervening command.
- Out of scope: any restructuring of `git.py`. This is the minimal fix to stop
  the failure in live repos; the broader cleanup is `simplify-git-sync`. Note
  for that ticket, not this one: `recurring_runner._rebase_checked_out_branch_onto`
  is yet another integrate-remote routine, so after this fix there are still
  three.
- Dogfooding hazard: this ticket's own launch teardown runs the code it
  changes. A `[git] refresh failed` line at the end of the implement or
  self-qa step is a signal about the change, not noise.
- Companion ticket: `simplify-git-sync` (design first). Land this one first.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
