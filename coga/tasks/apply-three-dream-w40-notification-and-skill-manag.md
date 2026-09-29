---
title: Apply three Dream W40 notification and skill-management corrections after PR
  914 lands
status: blocked
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
step: 1 (implement)
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

## Blockers

- [ ] [2026-09-29 12:11] [agent:claude] id=20260929T121100 Depends on fix-recurring-sweep-git-hygiene-blocked-task-escap: merge or close PR #914 (https://github.com/FastJVM/coga/pull/914) before applying these three corrections, as this ticket requires. PR #914 is still OPEN as of 2026-09-29; overlapping PR #911 has merged.

- [ ] [2026-09-29 12:14] [agent:claude] id=20260929T121459 Depends on fix-recurring-sweep-git-hygiene-blocked-task-escap: merge or close PR #914 (https://github.com/FastJVM/coga/pull/914) before applying these three corrections. Verified PR #914 is still OPEN; the existing prerequisite remains unresolved.
