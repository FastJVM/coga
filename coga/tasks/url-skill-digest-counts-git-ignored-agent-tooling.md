---
title: URL skill digest counts git-ignored agent-tooling files as local adaptation
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
launch_generation: pending:ada9bb4d-48ea-4b70-8f2a-2866689ef8b9
---

## Description

Filed by Dream 2026-W40, Phase 6 (shard ks-23, class gap; targets `src/coga/skill_manager.py::hash_skill_tree` and `docs/contexts/coga/skill-management/SKILL.md` URL-backed provenance rules). The 2026-09-29 skill-update report listed `clarity` as `skipped-local-adaptation` ("local files differ from recorded installed digest; upstream digest unchanged") four days after canceled `implement-the-include-allowlist-that-url-skill-upd` verified it clean. Recomputing the digest shows the only divergence is `coga/skills/clarity/.claude/launch.json`, a git-ignored agent-tooling artifact: with it the tree hashes to `8a64265c…`, without it to exactly the recorded `a6d3504a…`. `hash_skill_tree` hashes every file, including ignored machine-local state (`.claude/`, `.codex/`, `.agent-skills/`, `__pycache__/`), so such an artifact turns a clean URL skill into a standing follow-up on one machine only. Decide: skip the same local-artifact set the packaging twin comparison already excludes (or git-ignored files) when hashing, and state the rule in `coga/skill-management`. Keep the skill-management edit coordinated with open PR #914, which also edits that topic.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: skill-digest-skip-local-artifacts

Plan: `src/coga/skill_manager.py::hash_skill_tree` skips any path with a
component in a fixed machine-local set (`.coga`, `.venv`, `.agent-skills`,
`.claude`, `.codex`, `__pycache__`) — the same set as
`tests/test_packaging.py::GENERATED_TEMPLATE_DIRS`. Chose a fixed set over
`git check-ignore`: hashing must stay pure/deterministic (also runs on
materialized downloads in temp dirs outside any repo). PR #914 is already
merged, so no topic-edit coordination needed.

## Handoff (implement)

- `src/coga/skill_manager.py`: new `LOCAL_ARTIFACT_DIRS`; `hash_skill_tree`
  skips any file whose parent path contains one of those names. Applies to
  both `installed_tree_digest` and `source_tree_digest` (same function), so
  existing recorded digests stay valid unless they included such files.
- Regression test
  `tests/test_skill_manager.py::test_url_update_ignores_machine_local_agent_tooling_artifacts`
  (fails without the fix; update reports `unchanged`).
- `coga/skill-management` topic (canonical + bootstrap twin): new
  "Tree digests skip machine-local state" bullet under URL-backed provenance
  rules. PR #914 was already merged; no conflict.
- Tradeoff noted in topic: an upstream change confined to those dirs is not
  detected. Live `coga/skills/clarity` digest still matches its record.
- Verification: `.venv/bin/python -m pytest` → 3161 passed.
