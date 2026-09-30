---
title: Make branch-sweep retirement survive an existing remote retired/ tag
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (self-qa)
launch_generation: pending:098aecb2-7a4d-40c8-9c8e-6e4349ec339b
---

## Description

## What broke

The `recurring/autoclose-merged` run ended with exit 2 and the ticket stuck in `in_progress`. The exit 2 came from the `branch-sweep` recipe, which `coga/recurring/autoclose-merged/ticket.py` runs every day through `run_recipe(..., "branch-sweep", [])`. Every other branch in the pass was handled normally. One branch failed:

```
Branch sweep: 'codex/retro-independent-clone-worklist-knowledge' could not publish
'retired/codex/retro-independent-clone-worklist-knowledge': To https://github.com/FastJVM/coga/
 ! [rejected]  retired/codex/retro-independent-clone-worklist-knowledge -> retired/codex/retro-independent-clone-worklist-knowledge (already exists)
hint: Updates were rejected because the tag already exists in the remote. — left in place.
```

This will happen again on every daily run. The branch stays because it could not be archived. On the next pass the sweep finds the local `retired/...` tag it created this time, sees that it matches the target, and pushes again. The push is rejected again, so autoclose-merged exits 2 again and its period task never finishes.

## Where it lives

`src/coga/branchsweep.py`, `_publish_retirement_tag` (around lines 384–453):

- The tip fetch uses `--no-tags`, and the function only checks for a **local** `refs/tags/retired/<branch>`. It never looks at the remote tag.
- The push is `git push --no-follow-tags <remote> refs/tags/X:refs/tags/X` with no force. The comment says "conflicting remote tags are rejected; identical tags retry". That describes the same-object case. A push that git rejects as "already exists" means the remote tag points at a **different** object. Most likely an earlier sweep retired this branch at an older tip, and the branch was later recreated or advanced under the same name.
- Any entry in `retirement_failures` makes the recipe return 2 (see around lines 709–736). So one unresolvable name conflict fails the whole recurring job.

## What a fix has to do

1. Before creating or pushing, read the remote tag (`git ls-remote --tags <remote> refs/tags/retired/<branch>`, or fetch just that tag):
   - **Remote tag's commit equals `target`, or `target` is its ancestor:** the tips are already preserved. Treat the branch as archived and continue to deletion. Do not push.
   - **Remote tag's commit does not contain `target`:** keep the old archive untouched and never force. Publish under a distinct, deterministic name, for example `retired/<branch>/<short-sha>` or a numbered suffix. Only if that also fails, report it as a failure.
2. Stop leaving a local tag that disagrees with the remote. Either create the local tag only after a successful push, or reconcile it with the remote result, so the next run does not replay the same conflict.
3. Update the module docstring (lines 36–39) and the owning contexts topic (the branch-sweep / `dev/checkout-cleanup` contract under `docs/contexts/`) to describe how a name collision is resolved. Keep the packaged twin in sync.
4. Add a test in `tests/test_branchsweep.py` (or wherever branch-sweep tests live). Pre-seed the remote with `retired/<branch>` at a different commit, then assert that the sweep archives the branch and exits 0 in two cases: the remote tag already contains the target, and the tips diverge.
5. Once the fix lands, run the recurring sweep again so the stuck `recurring/autoclose-merged` task for this period can finish, and remove the stray local tag `retired/codex/retro-independent-clone-worklist-knowledge` if it is still there.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Diagnosis (from recurring/autoclose-merged period agent, 2026-09-30)

- Failing clone: `/home/n/Code/claude/coga` (recurring control clone). Local
  branch `codex/retro-independent-clone-worklist-knowledge` = `2d1ee292a`,
  local tag `retired/...` also `2d1ee292a`.
- Remote tag `retired/codex/retro-independent-clone-worklist-knowledge` =
  `82461f50b`, published by another clone (`/home/n/Code/coga` no longer has the
  branch). `82461f50b` is PR #920's merged head (squash-merged, not on main).
- `2d1ee292a` is an ancestor of `82461f50b`: this clone holds a stale earlier
  tip, so nothing would be lost. Candidate rule: when the remote `retired/` tag
  exists and the local tip is an ancestor of (or equal to) it, treat the archive
  as already published instead of failing; a non-ancestor tip should still
  refuse (and probably archive under a distinct name).
- Current proofs would still refuse the branch delete (tip != merged head), so
  the fix should decide whether "ancestor of an archived merged head" vouches.

## Dev

branch: branch-sweep-retired-tag-collision

Plan: `_publish_retirement_tag` reads the remote tag first (`ls-remote`);
a remote archive that contains the target counts as published; a divergent
one sends the archive to `retired/<branch>@<sha12>` (`/<sha>` would D/F-clash
with the existing tag ref). Local tag is created only after publication.

## Implement handoff (2026-09-30)

Pushed `branch-sweep-retired-tag-collision` (1 commit, rebased on origin/main;
full `pytest` 3138 passed).

- `src/coga/branchsweep.py` `_publish_retirement_tag`: one `ls-remote --tags`
  for `retired/<b>` and `retired/<b>@<sha12>`. For each name in order, a
  remote tag equal to or containing target means already archived (no push).
  Remote at unrelated history, or an unpublished local tag at a different
  commit, means the name is taken, so try the next one. Otherwise push
  `target:refs/tags/<name>` (no force, `--no-follow-tags`). New helpers
  `_archived_commit` (fetches a missing remote tag object) and
  `_mirror_local_tag` (local tag is created only after publication and
  fast-forwarded only when the archive contains it). Both names taken means
  refuse (exit 2).
- Decision: `@<sha12>`, not `/<sha>`. A ref cannot nest under the existing
  `refs/tags/retired/<b>` (D/F conflict).
- Decision: an archive that contains the target now vouches. This reverses
  the old "covering descendant is deliberately insufficient" rule in
  `dev/checkout-cleanup`, as the ticket asks. The partial-cleanup retry test
  was renamed to `test_partial_cleanup_retry_trusts_archive_containing_remote_tip`,
  and it now expects the remote ref to be deleted.
- Tests: the old conflicting-tag test was replaced by
  `test_conflicting_retirement_tag_is_kept_and_tip_archived_under_its_sha`.
  Added tests for the containing archive (the diagnosed lagging-clone shape;
  asserts no tag push), for both names taken, and for a retry of the @-name.
  The remote-listing-failure test now fakes only `ls-remote --heads`.
- Docs: module docstring plus the `dev/checkout-cleanup` context, canonical
  and packaged twin, which are byte-identical.
- Still open (ticket item 5, after merge): rerun the recurring sweep in
  `/home/n/Code/claude/coga`. The fix fast-forwards that clone's stale local
  tag `retired/codex/retro-independent-clone-worklist-knowledge` to the remote
  commit, so deleting the tag by hand is optional.
