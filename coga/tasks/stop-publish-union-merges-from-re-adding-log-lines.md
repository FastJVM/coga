---
title: Stop publish union merges from re-adding log lines already on control
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

`git.publish` can add a second copy of a `coga/log.md` line that is already on control. The invariant to establish: a union-merged publication never lands a line that control already has a second time. The design step chooses how. It could change the base selection, add a merge rule, or both, and records the choice and the reason in `coga/internals/spool-merge`.

Done when:
- a regression test for the reproduction below lands a single copy;
- concurrent appends on both sides still survive, with a test;
- a line removed only in the working copy still comes back, with a test (union never deletes, and the `retires.md` reader relies on that);
- the case where control is not a descendant of HEAD, with the merge-base far back or absent, is covered;
- `_published_proof` agrees with `_build_tree` on the reproduction;
- `coga/internals/spool-merge` describes the new contract.

## Context

Split out of `prevent-duplicate-session-usage-records-from-infla` (2026-10-09). That ticket dedupes usage records at read time (`usage.load_records`, exact JSON message text). This one fixes the writer-side root cause.

- Mechanism (verified against the code): `git.publish` takes `ancestor = merge-base(HEAD, <control>)`. `git._build_tree` merges `merge=union` paths with `_merge_union_bytes(current=<control blob>, base=<ancestor blob, or b"" when there is none>, other=<working>)`, which shells out to `git merge-file --union`. When HEAD lags a line already on control, and that line sits at a different position in the working copy, the line is emitted twice. Reproduced: base `A`, control `A X Y`, working `A Z X` → `A X Y Z X`. A same-position case (working `A X Z`) keeps one copy. With `ancestor=None` the base is `b""`, so every working line not already on control is treated as a fresh add.
- Second call site, in scope: `git._published_proof` also calls `_merge_union_bytes`, with HEAD's blob as base. It decides whether the working copy is already on control for prepare and the handoff, so the same layout yields a false "lines not yet on control". It has to agree with `_build_tree`.
- Open question for design: establish first how the working copy comes to hold X after Z in practice, whether through a peer publish or a fast-forward of the landed bytes. If it is the latter, `refs/worktree/coga/published` (the merged blob this worktree last landed) may be a better base than the merge-base.
- Candidate fixes, for the design step to weigh:
  - (a) Use the newest known common copy as base: the published ref, or control's copy when HEAD's copy is its prefix. Minimal, but it has to handle a missing published ref and other worktrees.
  - (b) Post-filter: drop working-side added lines that already appear on control. Simple and position-independent. Safe for `log.md`, whose lines are effectively unique because they carry timestamps, but it would collapse intentional repeated lines in `retires.md`.
  - (c) Append-only merge: take control's copy, then append working lines past the longest common prefix. This breaks `retires.md`, which is rewritten rather than appended to.
- Evidence: across this repo, magicator, multiply, and thinkpick, 24 duplicated usage records. Each extra copy came from a later single-parent publish commit (`Log: …`, `Sync coga state`, `Ticket: …`), never from a merge commit or a double write. Example: `c8a3cdfda` re-adds a record that its parent `276448100` had already added.
- Affects every `log.md` line (audit lines such as `launched` too) and `retires.md`, not only usage records.
- Tests: publish tests live in `tests/test_git.py` (the `git_repo` fixture and helpers such as `push_competing_commit`). Templates: `test_prepare_proves_a_union_log_published_after_control_moved`, `test_subsumed_guard_union_merges_committed_log_lines`, `test_publish_refuses_to_delete_a_missing_union_merged_log`.
- Topics are cited, not attached:
  - `coga/internals/spool-merge` (`docs/contexts/coga/internals/spool-merge/SKILL.md`) is the topic this ticket edits.
  - `coga/internals/state-publication` (`docs/contexts/coga/internals/state-publication/SKILL.md`): read its union-merge and publish/prepare sections, and update it in the same PR if the publication contract changes.
  - `coga/internals/git-regressions` (`docs/contexts/coga/internals/git-regressions/SKILL.md`) covers `_guard` and the missing-union refusal.
- Related: `tell-agents-never-to-git-commit-coga-task-and-log` covers the squash-merged-PR variant (#732, `81cefcb7f`).
- Out of scope: do not rewrite existing logs. Historical duplicates are handled by reader dedupe.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
