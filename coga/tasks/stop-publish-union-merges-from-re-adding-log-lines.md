---
title: Stop publish union merges from re-adding log lines already on control
status: in_progress
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
step: 3 (review-design)
agent: claude
---

## Description

`git.publish` can land a second copy of a `coga/log.md` (or `retires.md`) line that control already has. The invariant this ticket establishes: **a union-merged publication never adds a line that control already has.** Both union call sites must enforce it identically: `_build_tree`, which builds the landed bytes, and `_published_proof`, which decides "already on control" for prepare and the subsumption realignment.

**How it happens in practice (verified in design).** A feature-branch or detached checkout publishes without its HEAD ever advancing, and `fast_forward_control` only rewrites the working copy to the landed bytes in a checkout that holds control. Sequence: control is `H`; a peer lands `P`; this checkout appends `M1` and publishes, which lands `H P M1` on control while its own working copy stays `H M1`. It appends `M2` and publishes again. Now `ancestor = merge-base(HEAD, control)` is still `H`. Diffed from `H`, control inserted `P M1` and the working copy inserted `M1 M2` at the same point, so `git merge-file --union` concatenates both insertions and lands `H P M1 M1 M2`. This was reproduced through the public `publish` API on the `git_repo` fixture: a `feature/x` checkout, `push_competing_commit` of `base + "peer line\n"`, then two `append_log` + `publish` rounds; control ended with `mine one` twice. The same mechanism applies when there is no merge-base at all (`ancestor=None`, base `b""`).

**Decision (owner, 2026-10-09): post-merge duplicate filter, not a new base.** Keep the existing base selection and `git merge-file --union`, then drop from the merged result every line the merge *inserted* (relative to control's copy) that equals a line control's copy still contributes to the result. Why not a better base: `refs/worktree/coga/published` holds the *landed* blob (`H P M1`). Used as the base, it makes the working copy look like it deleted `P`, so the clean merge would erase the peer's line. A correct base would need a new per-worktree ref recording the working bytes at the last publish. That adds hidden state and still fails with no ref, in another clone, or with no merge-base. The filter is position-independent and covers every base. **Accepted tradeoff:** a line identical to one control already has can never be added again. That is harmless for `retires.md`, whose reader collapses duplicates. For `log.md` lines carry a minute timestamp and usage records carry session ids, so only an identical audit line written in the same minute and published separately would collapse.

**Deletion contract unchanged (owner, 2026-10-09).** Today a line the working copy dropped still lands as a deletion when the three-way base also had it (base `A L B`, control `A L B`, working `A B` → `A B`). `coga retire`'s slug drop from `retires.md` relies on that. The filter never removes a line that control contributes to the merge result, so it does not change this. A line the working copy lacks but the *base also lacks* (a concurrent control addition, or no merge-base) is kept. That is the "comes back" case the original ticket asked to test. The ticket's phrase "union never deletes" was inaccurate; the topic must state the precise rule instead.

### Acceptance criteria

- [ ] `_merge_union_bytes` (or one helper it calls) applies the duplicate filter. `_build_tree` and `_published_proof` both go through it, so `_local_control_subsumed` inherits it too, and no call site filters on its own.
- [ ] Regression, unit level: `_merge_union_bytes(current=b"A\nX\nY\n", base=b"A\n", other=b"A\nZ\nX\n")` returns `b"A\nX\nY\nZ\n"` (today `A X Y Z X`).
- [ ] Regression, end to end in `tests/test_git.py`: the feature-checkout sequence above (peer line, then publish `M1`, then append `M2` and publish) leaves control with exactly one `M1` line, plus `P` and `M2`.
- [ ] Concurrent appends survive: control gains a peer line and the working copy gains its own line from the same base; both land once. The existing `test_log_appended_on_both_sides_keeps_both_lines` stays green, and a unit case asserts the exact bytes.
- [ ] Comes back: a line control has that the working copy and the base both lack stays on control. Unit case: base `A`, control `A L`, working `A Z` → `A L Z`. The working-side deletion case (base `A L B`, control `A L B`, working `A B` → `A B`) is pinned as unchanged behavior.
- [ ] Moved line kept: base `A L B`, control `A L B`, working `A B L` keeps exactly one `L`. The filter only drops an insertion when control's copy of that line survives in the result.
- [ ] No merge-base: base `b""`, control `A X`, working `Q A X Z` → `A X Q Z` (today `A X Q A X Z`). Also add one `publish`-level test where `merge-base(HEAD, control)` is far back: a feature branch cut several control commits earlier, whose working log carries lines control already has at different positions, lands no duplicate.
- [ ] `_published_proof` agrees with `_build_tree`: for the reproduction layout (control `A X Y`, HEAD `A`, working `A X`), `_published_proof` returns `None` (today it reports "lines not yet on control"). With working `A Z X` it still reports "lines not yet on control", because `Z` is not on control. A prepare-level test on a feature checkout after the two-publish sequence: `prepare_control_checkout` succeeds and does not refuse with "lines not yet on control".
- [ ] Control's own lines are never reordered: the result keeps control's copy (minus working-side clean deletions) as an in-order subsequence.
- [ ] `docs/contexts/coga/internals/spool-merge/SKILL.md` and its packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/spool-merge/SKILL.md` describe the new contract in byte-identical text: the invariant, the filter, why the published ref is not the base, the deletion rule, and the identical-line tradeoff. `tests/test_packaging.py` passes.
- [ ] `docs/contexts/coga/internals/state-publication/SKILL.md` publish step 4 ("`merge=union` paths three-way union-merged") gains a short pointer to the duplicate filter in `coga/internals/spool-merge`, and the same change goes into its packaged twin if it has one.
- [ ] `python -m pytest` passes.

### Proposed shape

1. **`src/coga/git.py`, `_merge_union_bytes`**: keep the `git merge-file --union` call unchanged, then pass its output and `current` to a new private helper, for example `_drop_reinserted_lines(current: bytes, merged: bytes) -> bytes`. Return the helper's result.
2. **The helper** (stdlib only):
   - Split both inputs with `splitlines(keepends=True)`.
   - Align them with `difflib.SequenceMatcher(None, current_lines, merged_lines, autojunk=False)`. `autojunk=False` matters: logs exceed 200 lines and contain repeated lines.
   - From the `equal` opcodes, collect the set of lines control contributes to the result. Walk the opcodes and emit merged lines: all `equal` lines, and for `insert`/`replace` the merged-side lines *not* in that set.
   - Return the joined bytes.
   - Byte-level line comparison, keeps ends. A final line without a newline compares unequal to the same text with one; document this rather than normalize.
   - Fast path: if `merged.startswith(current)`, only the suffix needs filtering, against the set of `current`'s lines. This keeps the common append case cheap on an 8k-line log. Optional; implement only if the plain matcher is measurably slow in tests.
3. **No call-site changes** in `_build_tree` or `_published_proof`. Their docstrings, and `_local_control_subsumed`'s ("union-merging the local copy onto the target changes nothing"), stay true. Add one sentence to `_merge_union_bytes`'s new docstring naming the invariant and pointing at `coga/internals/spool-merge`.
4. **Tests** in `tests/test_git.py`:
   - Unit cases on `_merge_union_bytes`; a parametrized table is fine.
   - The feature-checkout publish regression.
   - The far-back merge-base publish case.
   - The `_published_proof` and prepare agreement cases.
   - Templates to follow: `test_prepare_proves_a_union_log_published_after_control_moved`, `test_log_appended_on_both_sides_keeps_both_lines`, `test_subsumed_guard_union_merges_committed_log_lines`.
5. **Docs**: rewrite the "How `publish` lands a union path" bullets in `coga/internals/spool-merge` (both twins). State the invariant, the filter, and the deletion rule (deletions the base saw still land; lines the base lacks are kept). Fix the `retires.md` bullet, which says a union "can duplicate a slug": publish no longer duplicates an identical line, but git-native merges, and differing lines for the same slug, still can, so the reader still collapses. Add the pointer in `coga/internals/state-publication`.

### Out of scope

- Rewriting or deduping existing `coga/log.md` / `retires.md` content. Historical duplicates are handled by reader dedupe (`usage.load_records`).
- Changing base selection (`merge-base(HEAD, control)`), `PUBLISHED_REF` semantics, or adding a new per-worktree ref.
- Changing deletion semantics for union paths ("union never deletes" is *not* adopted).
- Git-native `merge=union` merges outside `publish` (PR merges, rebases). The squash-merged-PR variant is `tell-agents-never-to-git-commit-coga-task-and-log`.
- Making the working copy of a non-control checkout track landed bytes.

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
- Design repro (2026-10-09): `_merge_union_bytes` base `A`, control `A W X Y`, working `A X Y S` → `A W X Y X Y S`, matching evidence commit `c8a3cdfda`. Its parent `276448100` landed orient-usage + `launched` on top of `394ce25bc`, whose `14:13` line the publishing checkout's working copy never had, and the next publish re-added both.
- `_merge_union_bytes` has exactly two callers, `_build_tree` and `_published_proof`; `_local_control_subsumed` reaches it through `_published_proof` with the merge base as `head_entry`.
- `PUBLISHED_REF` (`refs/worktree/coga/published`) is written by `_record_published` with landed blob oids. It is read only as provenance for non-union paths (see the `revs.append(PUBLISHED_REF)` site that `_provenance` uses).
- `retire_worklist` module docstring: the reader collapses duplicate slugs on parse, and `coga retire` drops its slug by rewriting the file. That drop reaches control as a clean three-way deletion.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design (2026-10-09, claude)

- Root cause confirmed through the public API: in a feature or detached checkout, HEAD never advances, so after one publish lands a peer line before this checkout's own line, the next publish re-adds that line. A scratch test reproduced it, then I removed the test.
- The owner chose the post-merge duplicate filter inside `_merge_union_bytes` over a new base ref. They kept today's deletion rule: a deletion the base saw still lands, and "union never deletes" is not adopted.
- Spec is under `## Description`. The `retires.md` bullet in spool-merge needs a wording fix in the implementation PR.

## Open Questions

- None outstanding. Both design choices were answered by the owner in-session (approach, deletion contract).

## Evaluator review

Cold review by Codex, 2026-10-09. **Not ready for implementation:** resolve the two must-fix findings below at owner review. No ticket-body, source, tests, branch, or PR changes were made.

### Must fix

1. **P1 — The proposed alignment can delete pre-existing control lines when neither side deleted anything.** `SequenceMatcher` equal blocks are not reliable provenance and need not cover control even when the raw merge contains all of it in order. Reproduced with the actual `src/coga/git.py::_merge_union_bytes` and an in-memory transcription of Proposed shape step 2 (each token is one newline-terminated line): base `A C A C`, control `A C A C A`, working `A C B A C`. Git returns `A C B A C A`, preserving every control line and adding only `B`. The proposed matcher instead aligns control's first `A C A` with the final `A C A`, labels the leading `A C B` an insertion, and labels control's final `C A` a deletion. Filtering its inserted `A C` returns `B A C A`, losing one existing `A` and one existing `C`. This violates the no-historical-dedupe scope, unchanged deletion behavior, and control-subsequence acceptance criterion. Repeated lines are explicitly supported (and historical duplicates remain on disk). Revise the alignment/filter specification to preserve surviving control occurrences, and require this exact regression to return the raw `A C B A C A`. The optional prefix fast path does not cover this example.

2. **P2 — The named positive `_published_proof` regression does not reproduce a failure.** Acceptance criteria says control `A X Y`, HEAD/base `A`, working `A X` currently reports “lines not yet on control.” Direct execution of `src/coga/git.py::_published_proof` with real fixture blobs returns `None` already; `_merge_union_bytes` already returns control unchanged. Keep this as a compatibility test if useful, but correct the baseline claim and add a case that actually fails before the fix. For example, control `A X Y`, HEAD/base `A`, working `A Y X` produces raw `A X Y Y X`; the current proof rejects it and the proposed filter would reduce it to control. Preserve the separate negative case containing new `Z`.

### Optional recommendations

- Clarify the ordering criterion alongside the moved-line case. With base = control `A L B` and working `A B L`, existing Git returns `A B L`, which the proposed helper preserves. State that ordering refers to surviving unmoved control occurrences, with clean moves treated as deletion/reinsertion, if that is intended; otherwise “control's own lines are never reordered” reads more broadly than the required moved-line behavior.
- If adopting the optional prefix optimization, require a complete-line boundary as well as `merged.startswith(current)`. An unterminated last control line can prefix a different merged line, so byte-prefix matching alone is not equivalent to the stipulated `splitlines(keepends=True)` comparison. Pin unterminated-line and repeated-line cases before optimizing.

### Verified scope and evidence

- `src/coga/git.py::_publish_locked`, `_build_tree`, `_published_proof`, `_local_control_subsumed`, `_record_published`, and `fast_forward_control` confirm the two shared merge callers, merge-base selection, landed-blob provenance ref, and feature-checkout behavior. The change belongs in existing shared Git infrastructure and is one coherent PR; no new ref or dispatch mechanism is needed.
- Re-ran the two-publish feature-checkout scenario using `tests/conftest.py::init_git_repo`, `GitRepo.push_competing_commit`, `logfile.append_log`, and public `git.publish` in a temporary repository: control contained `mine one` twice after `mine two` published. Scratch probes changed no repository source or tests.
- Read the owning `coga/internals/spool-merge` and `coga/internals/state-publication` topics, `coga/internals/git-regressions`, and `src/coga/retire_worklist.py` parsing/discharge paths. Both requested topic twins exist under `src/coga/resources/templates/coga/bootstrap/contexts/`; the proposed documentation scope fits the contract change.
- The ticket correctly places acceptance criteria, proposed shape, and scope under `## Description`. Topic citations identify the needed contracts. Its frozen workflow matches the packaged `code/design-then-implement` workflow and hands this review to the owner before implementation.
- Verification: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_git.py::test_log_appended_on_both_sides_keeps_both_lines tests/test_git.py::test_prepare_proves_a_union_log_published_after_control_moved tests/test_git.py::test_subsumed_guard_union_merges_committed_log_lines` → **3 passed**. Actual Git merge and proposed-filter probes established the counterexamples above. Full-suite validation is deferred to implementation; this step only reviewed the design.
