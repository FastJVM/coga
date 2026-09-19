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
branch the same way the publish half already does: fetch, rebase the local
control commits onto the fetched tip (`coga/log.md` union-merges, task files
are coga state), then push them. A refresh that ends with local control
matching `origin/<control>` is the definition of done. A genuine conflict
(product files diverged on `main`) stays a loud non-fatal miss, but the
message must say what the operator should run to recover.

## Context

- Refresh entry point: `git.refresh_coga_state_from_control`. The
  control-branch case is the short block `if branch == cfg.git_control_branch:
  _run_git(root, "merge", "--ff-only", "--quiet", tip); return True` right
  after `_fetch_branch_oid`. Everything else in that function is the
  feature-branch overlay and assist-publication path — leave it alone.
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
- Reproduction to encode as a test in `tests/test_git.py` (existing refresh
  tests start around `test_refresh_coga_state_no_remote_prints_calm_notice`;
  the `git_repo` fixture gives a checkout plus bare remote): commit coga state
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
- Contexts cited, not attached (both are large and only a section each
  matters): `coga/sync` (`coga/contexts/coga/sync/SKILL.md`, section
  `## Git — durable task-state sync`, the paragraph describing the launch-end
  refresh and its "on the control branch that is a plain `merge --ff-only`"
  sentence — update that sentence in the same PR, plus the packaged twin under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`,
  which `tests/test_packaging.py` requires to stay byte-identical);
  `coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`, test expectations:
  `python -m pytest tests/test_git.py`).
- Out of scope: any restructuring of `git.py`. This is the minimal fix to stop
  the failure in live repos; the broader cleanup is `simplify-git-sync`.
- Companion ticket: `simplify-git-sync` (design first). Land this one first.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
