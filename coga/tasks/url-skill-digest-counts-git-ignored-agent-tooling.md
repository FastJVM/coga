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
step: 3 (open-pr)
agent: claude
launch_generation: pending:023425f2-5239-4226-bdf7-48f0cc0293b3
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

## Peer review

- `codex review --base main` returned with one P2 finding: an unchanged
  pre-upgrade installation whose recorded hashes include excluded directories
  would falsely conflict. Fixed by verifying the legacy hash before accepting
  an old record. Update migrates verified provenance; status stays read-only;
  real local edits still block overwrites. Metadata-only repairs report
  `changed=True` so the skill-update PR flow publishes them.
- A second `codex review --base main` returned with no actionable findings.
- Added eight migration cases covering pruned/full installs, local edits,
  unchanged/changed upstream, metadata-only repairs, and repeat-update no-ops.
  Expanded artifact coverage to all six excluded directories. Canonical and
  bootstrap skill-management topics document compatibility behavior.
- Verification: `PYTHONPATH="$PWD/src" .venv/bin/python -m pytest
  tests/test_skill_manager.py tests/test_packaging.py -q` → 117 passed;
  `PYTHONPATH="$PWD/src" .venv/bin/python -m pytest` → 3169 passed;
  `git diff --check` passed. Live clarity's current digest matches its record.
  No terminal or rendered-message surface changed, so no interactive gate applies.
- Ran `git fetch origin main` and `git rebase FETCH_HEAD` successfully onto
  `c85dea144`; committed the fix as `fda915f69`, then pushed the branch with
  `--force-with-lease`. Two code commits remain ahead of main. Returned to a
  clean main at `1ef9d66d7` before this handoff; intervening main changes were
  only other tickets and the audit log.

## PR

URL-installed skills could report local adaptation solely because an agent
created `.claude/launch.json` inside the skill. Exclude the fixed machine-local
directory set used by packaging from installed and upstream tree digests,
keeping hashing independent of Git ignore configuration. Verify legacy hashes
before migrating older provenance so unchanged pre-upgrade installs continue
updating while real local edits remain protected. Document the exclusions and
migration in the canonical skill-management topic and its packaged twin.

Test plan: `PYTHONPATH="$PWD/src" .venv/bin/python -m pytest` → 3169 passed;
targeted skill-management/packaging suite → 117 passed; `git diff --check` passed.
