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
step: 1 (implement)
agent: claude
launch_generation: 807f6ad7-9aaa-40d7-84a1-935ff11a7080
---

## Description

Filed by Dream 2026-W40, Phase 6 (shard ks-23, class gap; targets `src/coga/skill_manager.py::hash_skill_tree` and `docs/contexts/coga/skill-management/SKILL.md` URL-backed provenance rules). The 2026-09-29 skill-update report listed `clarity` as `skipped-local-adaptation` ("local files differ from recorded installed digest; upstream digest unchanged") four days after canceled `implement-the-include-allowlist-that-url-skill-upd` verified it clean. Recomputing the digest shows the only divergence is `coga/skills/clarity/.claude/launch.json`, a git-ignored agent-tooling artifact: with it the tree hashes to `8a64265c…`, without it to exactly the recorded `a6d3504a…`. `hash_skill_tree` hashes every file, including ignored machine-local state (`.claude/`, `.codex/`, `.agent-skills/`, `__pycache__/`), so such an artifact turns a clean URL skill into a standing follow-up on one machine only. Decide: skip the same local-artifact set the packaging twin comparison already excludes (or git-ignored files) when hashing, and state the rule in `coga/skill-management`. Keep the skill-management edit coordinated with open PR #914, which also edits that topic.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
