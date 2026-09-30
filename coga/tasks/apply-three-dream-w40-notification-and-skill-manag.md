---
title: Apply three Dream W40 notification and skill-management corrections after PR
  914 lands
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

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). These findings target files that open PR #914 (branch `fix-recurring-git-hygiene`, "Fix recurring sweep git hygiene") edits, and #914's diff does not carry them. Apply after #914 merges or closes; keep live/packaged twins byte-identical.

1. `docs/contexts/coga/notifications/producers/SKILL.md` (Dream shard ks-19, class stale): `src/coga/recurring_runner.py::_flag_period_contradiction` (added in #892) sends `notify(kind="recurring-error", important=True, fatal=False)`, but the Outcome-surface table lists no such producer. Add the row; also add it to the best-effort important alerts in `coga/notifications/failures` (file also edited by open PR #911) and the enumerated routed failures in `coga/important`.
2. `docs/contexts/coga/skill-management/SKILL.md` (shards ks-22, ks-29, class stale): the per-skill update argv is spelled `gh skill update --dir coga/skills <ref>`, but `skill_manager._update_gh_backed_skill` runs `gh skill update --dir <root> --all <ref>`; without `--all` gh exits 1 non-interactively whenever an update exists. Add `--all` plus a clause that it only suppresses gh's confirmation.
3. Same topic, extract from canceled ticket `v2/skill-update-aborts-on-uncommitted-log-file` (shard ks-34, class extract, source: canceled): `coga skill update --all --pr` carries updates with `git checkout -B coga/skill-update <control-branch>` and its only preflight (`_assert_no_unmerged_paths`, `--diff-filter=U`) misses ordinary dirty tracked files, so a dirty file the checkout would overwrite surfaces as git's raw "Your local changes ... would be overwritten" (exit 2). Record this known failure mode (or fix the preflight). Leave the canceled source ticket on disk.

Verification: `python -m pytest tests/test_packaging.py`.

## Context

<!-- coga:blackboard -->

## Dependency check — 2026-09-29

- Resolved: PR #914 merged at `2026-09-29T22:54:15Z`, verified via
  `gh pr view 914 --json number,state,mergedAt,closedAt,headRefName,title,url`.
  All four prerequisite asks were resolved with `coga unblock`; the earlier
  checks below are historical.
- `gh pr view 914 --json number,state,mergedAt,headRefName,title,url` confirms
  [PR #914](https://github.com/FastJVM/coga/pull/914) is still `OPEN` on
  `fix-recurring-git-hygiene`. Its owning task is
  `fix-recurring-sweep-git-hygiene-blocked-task-escap`, currently at the
  owner-controlled review step. This ticket explicitly requires #914 to merge
  or close before these corrections are applied.
- The same check for [PR #911](https://github.com/FastJVM/coga/pull/911)
  confirms it merged at `2026-09-29T18:51:15Z`; that overlap is cleared.
- Start check passed: clean `main`, fresh `git fetch origin main`, and
  `git merge --ff-only origin/main` reported already up to date. No feature
  branch or implementation changes were made, and tests were not run while
  the prerequisite remains open.
- Resume after #914 merges or closes, refresh `main`, and recheck all three
  corrections against the landed topics. Plan: document the dirty-tracked-file
  failure rather than change the preflight, preserve the canceled source
  ticket, and keep every edited topic byte-identical to its packaged twin.

---

## Dev

branch: dream-w40-notification-skill-docs

- Start check: clean `main`, fetched `origin/main`, fast-forward already current.
- Plan: correct the notification inventory/routing/failure topics and per-skill
  update argv; document the existing dirty-tracked-file checkout failure in
  skill-management without changing runtime behavior. Keep all four packaged
  twins identical and leave the canceled source ticket untouched.

## Implementation handoff — 2026-09-29

- Pushed commit `728a1ec35` on `dream-w40-notification-skill-docs`.
  Four canonical topics and their packaged twins changed; no runtime changes.
- Added `recurring_runner._flag_period_contradiction` to the outcome producer
  inventory, best-effort important alerts, and important routing inventory.
- Corrected the per-ref gh update argv to include `--all`, explaining that it
  suppresses confirmation while the explicit ref still selects one skill.
- Documented the existing dirty-tracked-file failure in skill-management:
  `skill_manager._assert_no_unmerged_paths` only checks unmerged paths, while
  `_commit_skill_updates` / `_checkout` can surface Git's overwrite refusal
  through `commands.skill._bail` (exit 2). Preflight behavior is unchanged.
  `coga/tasks/_v2/skill-update-aborts-on-uncommitted-log-file.md` is untouched.
- Verification: `.venv/bin/python -m pytest tests/test_packaging.py`:
  **23 passed**; `PYTHONPATH=$PWD/src .venv/bin/python -m pytest`:
  **3135 passed** in 209.89s; `git diff --check` passed. All four topic twins
  were also compared byte-for-byte. No fixture or validation behavior changed.
- Freshened onto latest `origin/main` before pushing. The sole incoming commit
  was this attempt's pre-branch Coga state publication (`285baf9e2`), changing
  only this ticket and the log; tested code and topics were unchanged.
- Returned to clean `main`, fast-forwarded to `origin/main`. No PR opened;
  the next workflow step is peer review. No remaining implementation blockers.

## Blockers

- [x] [2026-09-29 12:11] [agent:claude] id=20260929T121100 Depends on fix-recurring-sweep-git-hygiene-blocked-task-escap: merge or close PR #914 (https://github.com/FastJVM/coga/pull/914) before applying these three corrections, as this ticket requires. PR #914 is still OPEN as of 2026-09-29; overlapping PR #911 has merged.
  resolved: [2026-09-29 21:24] [human:nicktoper] PR #914 merged at 2026-09-29T22:54:15Z, verified with gh pr view 914. This satisfies the merge-or-close prerequisite in all four open blocker asks; PR #911 had already merged. Proceed with the three scoped documentation corrections.

- [x] [2026-09-29 12:14] [agent:claude] id=20260929T121459 Depends on fix-recurring-sweep-git-hygiene-blocked-task-escap: merge or close PR #914 (https://github.com/FastJVM/coga/pull/914) before applying these three corrections. Verified PR #914 is still OPEN; the existing prerequisite remains unresolved.
  resolved: [2026-09-29 21:24] [human:nicktoper] PR #914 merged at 2026-09-29T22:54:15Z, verified with gh pr view 914. This satisfies the merge-or-close prerequisite in all four open blocker asks; PR #911 had already merged. Proceed with the three scoped documentation corrections.

- [x] [2026-09-29 14:26] [agent:claude] id=20260929T142650 Depends on fix-recurring-sweep-git-hygiene-blocked-task-escap: PR #914 (https://github.com/FastJVM/coga/pull/914) remains OPEN. Merge or close it before applying these three corrections, or explicitly waive that prerequisite. Both existing asks remain unresolved.
  resolved: [2026-09-29 21:24] [human:nicktoper] PR #914 merged at 2026-09-29T22:54:15Z, verified with gh pr view 914. This satisfies the merge-or-close prerequisite in all four open blocker asks; PR #911 had already merged. Proceed with the three scoped documentation corrections.

- [x] [2026-09-29 15:46] [agent:claude] id=20260929T154639 Depends on fix-recurring-sweep-git-hygiene-blocked-task-escap: PR #914 (https://github.com/FastJVM/coga/pull/914) is still OPEN with no mergedAt or closedAt. Merge or close PR #914, or explicitly waive this ticket prerequisite, before applying the three corrections. All three existing blocker asks remain unresolved.
  resolved: [2026-09-29 21:24] [human:nicktoper] PR #914 merged at 2026-09-29T22:54:15Z, verified with gh pr view 914. This satisfies the merge-or-close prerequisite in all four open blocker asks; PR #911 had already merged. Proceed with the three scoped documentation corrections.
