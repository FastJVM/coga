---
title: State sync published unmerged recurring templates from a feature branch
status: draft
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
contexts:
  - coga/sync
  - coga/internals/state-publication
  - coga/internals/state-publication/sweep
  - coga/internals/git-refresh
  - coga/packaging
  - coga/testing
  - dev/checkouts
---

## Description

On 2026-10-16 the catch-all sweep commit 0591ae8bd ("Sync coga state", 11:24) published to main the unmerged scope: clone versions of coga/recurring/{autoclose-merged,branch-sweep,upstream-coga}/ticket.{md,py} from the in-progress branch clone-scoped-recurring (ticket run-clone-local-recurring-work-in-every-clone). Core on main has no scope: clone, so autoclose-merged stopped running branch-sweep, upstream-coga stopped bumping its period task, and test_live_and_packaged_copies_stay_identical failed. PR #1032 restores the files.

The leaked content equals branch commit 5abc520d5, committed at 11:16, before the sweep. coga/internals/state-publication says committed edits on a feature branch stay with the branch unless they are routine state; only dirty files in the roots are the documented pre-review hazard. So either the files were still dirty in the sweeping checkout (another worktree, or edits after the commit), the commit sat on local main and was published as a hand commit on local control, or _candidates misclassifies committed recurring templates as routine state.

### Acceptance criteria

- [ ] Reproduce or pin down which of the three paths published 0591ae8bd, with evidence from git reflog, coga/log.md, and the _candidates code path.
- [ ] If it is a _candidates or hand-commit bug, fix it so that committed, unmerged edits to recurring templates (and other non-routine Coga-root files) on a feature branch never reach control through the sweep. Add a regression test.
- [ ] If it is the accepted dirty-file hazard, decide with the owner whether recurring ticket.py and templates whose packaged twin differs should be excluded from the sweep, or at least refused when they would drift from their packaged twin. Record the decision in coga/internals/state-publication and its packaged twin.
- [ ] Full suite and coga validate --json pass.

## Context

Found 2026-10-16 in an attended `coga chat` while fixing the twin-drift test failure. Code: `git.sync_coga_state` → `publish` → `_candidates` in `src/coga/git.py`. The leaked work is preserved on `origin/clone-scoped-recurring`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
