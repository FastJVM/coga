---
title: Branch-sweep never clears rebased-copy branches
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
step: 3 (open-pr)
agent: claude
---

## Description

Filed by Dream 2026-W40, Phase 6 (shard ks-23, class gap; targets `src/coga/branchsweep.py::merged_pr_verdict` and `coga/skills/coga/branch-sweep/sweep/SKILL.md`). The branch-sweep skill's step 4 documents that a local ref whose commits were rebased in another checkout and then merged is refused "on every pass, until a human deletes it", and says neither the manual clearance (`git cherry` proof + `git branch -D` / `git push --delete`) nor a patch-id extension of `merged_pr_verdict` "is owned by a ticket yet". The 2026-09-28 sweep still skipped the six refs listed on 2026-09-21 (`branch-sweep-landed` #811, `dream-w38-extract-backlog` #812, `sweep-abandoned-record` #813, `recurring-missing-workflow` #814, `title-only-validator` #815, `v2-premise-holes` #819) and added five more (`bloated-blackboard-remedy` #856, `codex/retro-recurring-branch-sweep-knowledge` #859, `doc-context-boundary` #790, `shebang-exec-check` #800, `skill-update-per-skill` #796); the set grows weekly and is re-reported daily by autoclose's branch pass. Decide: extend `merged_pr_verdict` with a patch-id / `git cherry` equivalence check for merged PRs, or own the recurring manual clearance. Open PR #914 edits `branchsweep.py` for other reasons (it does not address this); coordinate with it. Owner search found only the done `branch-sweep-strands-squash-merged-branches-whose` (lagging refs, not rebases).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Blockers

- [x] [2026-09-30 11:08] [agent:claude] id=20260930T110837 Start check failed: /home/n/Code/coga has an unpublished blackboard edit on another ticket (coga/tasks/autofix/make-branch-sweep-retirement-survive-an-existing-r/ticket.md, a 16-line 'Diagnosis (from recurring/autoclose-merged period agent, 2026-09-30)' section, modified 10:50). Please publish (commit+push to main) or discard that edit so the checkout is a clean main, then unblock and relaunch.
  resolved: [2026-09-30 15:16] [human:nicktoper] Stray edit to autofix/make-branch-sweep-retirement-survive-an-existing-r was published to main (Diagnosis section committed); checkout verified clean main at origin/main a9509a5dd.

## Dev

branch: branch-sweep-cherry-pick

Initial plan (agreed with human 2026-09-30; refined in peer review below): extend `branchsweep.merged_pr_verdict` so
commits patch-equivalent to the merged head drop out of the "beyond" listing
(`git rev-list --right-only --cherry-pick <head>...<tip> ^<landed>`); remaining
commits still face the state-only path check. Remote refs stay exact-tip only.
Update sweep skill step 4 + packaged twin. PR #914 already merged — no
coordination needed. The 11 listed local refs are already gone here; the 4
surviving remote refs sit at their exact merged heads and should clear on the
next sweep.

## Handoff (implement, 2026-09-30)

Commit `621cae633` on `branch-sweep-cherry-pick` (pushed; up to date with main).

What changed:
- `branchsweep.merged_pr_verdict`: the "beyond" listing is now
  `git rev-list --right-only --cherry-pick <head>...<tip> ^<landed>`, so
  commits patch-equivalent to the merged head drop out. Leftovers still face
  the state-only path check; merges have no patch-id and are never dropped.
- `branchsweep._publish_retirement_tag` (new kw `pr_heads`, helper
  `_containing_tip`): **decision by human** — when the tips diverge, a tip
  that is a merged PR head is left to GitHub's `refs/pull/<n>/head` and the
  tag archives the rest; a note names the PR ref. This was needed because a
  rebased copy's remote sits at the merged head while the local ref keeps its
  pre-rebase commits, so the verdict fix alone turned "skipped" into an
  archive failure (recipe exit 2). Divergent tips that no PR ref covers
  (e.g. both tips are merged heads) still refuse.
- Docs: `dev/checkout-cleanup` retirement paragraph and sweep skill step 4
  (the "refused by design" paragraph removed), plus packaged twins.
- Tests (`tests/test_branchsweep.py`): `test_local_ref_rebased_elsewhere_then_merged_is_deleted`,
  `test_local_ref_whose_rebase_changed_the_patch_is_kept`; the old divergent
  refusal test now uses two merged heads
  (`test_divergent_merged_heads_are_preserved_when_one_tag_cannot_cover_both`)
  since its former shape is now archived by design.

Verification: `.venv/bin/python -m pytest -q` → 3137 passed. (System
`python` lacks `tomlkit`; use the repo `.venv`.)

Notes for review: the four surviving remote refs (`codex/retro-recurring-branch-sweep-knowledge`,
`doc-context-boundary`, `shebang-exec-check`, `skill-update-per-skill`) sit
at their exact merged heads with no local copies, so the next sweep should
delete them without this change.

## Peer review

2026-09-30, Codex: both reviews **returned** before handoff.

- `codex review --base main` returned one P2: ordinary patch IDs ignore
  whitespace and can approve deletion after a rebase changes Python
  indentation. A separate real-Git reproduction also showed that excluding
  control before matching strands rebased copies after normal merges.
- The human approved the revised fix: whitespace-sensitive comparison
  independent of control exclusions, accepting more Git work and conservative
  retention when patch context differs.
- `codex review --base origin/main` returned two P1 findings on that fix:
  set membership reused one merged patch for repeated local commits, allowing
  reapplied source work after a revert; `diff.submodule=log` could hide a
  changed gitlink from patch-ID parsing. This review's first invocation failed
  to initialize in the read-only sandbox; the escalated invocation returned.

All reported findings are addressed in `412fad124` and `9b3d50326`:
- `git patch-id --verbatim`, with byte-preserving subprocess IO, retains
  indentation and line-ending differences. Merged-side history stays available
  even when normal merges put it on control.
- Matches are consumed one-to-one. Submodule diffs use the explicit short
  format; external diff and text conversion are disabled.
- Real-Git regressions cover normal/squash merges, changed patches,
  indentation/line endings, comparison failure, repeated/reapplied patches,
  and submodule display configuration. Existing state-only and archive gates
  remain covered. The final small follow-up was verified with these tests;
  no third review was run.
- The owning `dev/checkout-cleanup` topic documents the proof; sweep skill
  step 4 summarizes and links to it. Both packaged twins match.

Final verification on `9b3d50326`:
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_branchsweep.py tests/test_packaging.py -q` → 105 passed.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q` → 3146 passed in 202.21s.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task branch-sweep-never-clears-rebased-copy-branches --json` → one task OK, no issues.
- `git diff --check origin/main...HEAD` passed. No raw-terminal, pager,
  prompt, or rendered UI surface changes require a separate interactive check.

Freshness: `git fetch origin main && git rebase FETCH_HEAD` completed without
conflicts before the final full suite. Branch tip `9b3d50326` has three code
commits ahead of `818d45724` and is published with
`git push --force-with-lease origin branch-sweep-cherry-pick`. Returned to a
clean `main` at `origin/main` before writing this handoff.

## PR

Branch sweep now clears local pre-rebase copies after their rebased PR merges.
It matches non-merge patches one-to-one with whitespace preserved, while
retaining unmatched source changes and the existing state-only checks.
Comparison works after both squash and normal merges and preserves branches
on comparison failure. Remote deletion still requires the exact merged head.

For divergent local and remote tips, the retirement tag preserves the local
history while the merged head remains available through its GitHub PR ref.
The cleanup contract, sweep instructions, and packaged twins document the
behavior. Real-Git regressions cover successful cleanup and refusal for
changed whitespace, reapplied work, changed gitlinks, and comparison failures.
Different patch context can conservatively leave an equivalent branch for
manual inspection.

Test plan: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q` → 3146 passed; `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_branchsweep.py tests/test_packaging.py -q` → 105 passed; `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task branch-sweep-never-clears-rebased-copy-branches --json` → no issues; `git diff --check origin/main...HEAD` passed on the feature branch.
