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
step: 1 (implement)
agent: claude
launch_generation: e35c6e39-ef85-42b6-a5b2-037bf65af7d6
---

## Description

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). These findings target files that open PR #914 (branch `fix-recurring-git-hygiene`, "Fix recurring sweep git hygiene") edits, and #914's diff does not carry them. Apply after #914 merges or closes; keep live/packaged twins byte-identical.

1. `docs/contexts/coga/notifications/producers/SKILL.md` (Dream shard ks-19, class stale): `src/coga/recurring_runner.py::_flag_period_contradiction` (added in #892) sends `notify(kind="recurring-error", important=True, fatal=False)`, but the Outcome-surface table lists no such producer. Add the row; also add it to the best-effort important alerts in `coga/notifications/failures` (file also edited by open PR #911) and the enumerated routed failures in `coga/important`.
2. `docs/contexts/coga/skill-management/SKILL.md` (shards ks-22, ks-29, class stale): the per-skill update argv is spelled `gh skill update --dir coga/skills <ref>`, but `skill_manager._update_gh_backed_skill` runs `gh skill update --dir <root> --all <ref>`; without `--all` gh exits 1 non-interactively whenever an update exists. Add `--all` plus a clause that it only suppresses gh's confirmation.
3. Same topic, extract from canceled ticket `v2/skill-update-aborts-on-uncommitted-log-file` (shard ks-34, class extract, source: canceled): `coga skill update --all --pr` carries updates with `git checkout -B coga/skill-update <control-branch>` and its only preflight (`_assert_no_unmerged_paths`, `--diff-filter=U`) misses ordinary dirty tracked files, so a dirty file the checkout would overwrite surfaces as git's raw "Your local changes ... would be overwritten" (exit 2). Record this known failure mode (or fix the preflight). Leave the canceled source ticket on disk.

Verification: `python -m pytest tests/test_packaging.py`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
