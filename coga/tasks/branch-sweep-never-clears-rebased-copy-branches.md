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
step: 2 (peer-review)
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

Plan (agreed with human 2026-09-30): extend `branchsweep.merged_pr_verdict` so
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

2026-09-30, Codex: `codex review --base main` **returned** with one must-fix
finding (P2): `--cherry-pick` uses whitespace-insensitive patch IDs. A rebased
copy that changes Python indentation can match the original patch despite
different behavior, authorize deletion, and remove the local ref/worktree.
The reviewer reproduced this false authorization. A separate scratch check
confirmed `git patch-id --verbatim` distinguishes those patches.

An additional real-Git reproduction found that a normal merge (rather than
a squash merge) still strands a rebased local copy: `^main` excludes the
merged head's commits before patch matching. Removing that exclusion from
the comparison produces the expected empty unmatched list.

Proposed fix, **awaiting the attending human's decision**: compute
whitespace-sensitive patch matches independently of control-history
exclusions, then apply the existing control/state-only gates. Add regressions
for indentation-changing rebases and normal merges. Tradeoff: more Git work
and conservative retention when patch context differs. No review fixes have
been applied and no bump has run; the attended-session instruction requires
confirmation before substantive code changes.

Verification:
- Reviewer: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_branchsweep.py tests/test_packaging.py -q` → 96 passed.
- After rebase: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q` → 3137 passed in 202.59s.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task branch-sweep-never-clears-rebased-copy-branches --json` → one task OK, no issues.
- `git diff --check` passed. No raw-terminal, pager, prompt, or rendered UI surface changes.

Freshness: `git fetch origin main && git rebase FETCH_HEAD` completed without
conflicts; `git push --force-with-lease origin branch-sweep-cherry-pick`
published `33f8a215b` atop `4ca7c1ada`. Returned to `main` before writing this
note. The final PR body remains to be authored after the review fixes.
