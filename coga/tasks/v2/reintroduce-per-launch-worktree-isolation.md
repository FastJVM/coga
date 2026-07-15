---
slug: v2/reintroduce-per-launch-worktree-isolation
title: Reintroduce per-launch worktree isolation
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Reintroduce per-launch `git worktree` isolation for `coga launch`, removed in
PR #547 (2026-07-14) after its fix tail showed the v1 design was more complex
than priced. Goal unchanged: several agents on different tickets run from one
clone without their `coga bump`/`mark` syncs contending a single `.git/index`
/ stash stack.

Design the v2 around the failure modes the v1 fix tail exposed, rather than
patching them one by one after shipping:

- Done-sentinel scoping across checkouts (v1: #519 — solved by `id_slug`
  scoping, which was kept and is already in place).
- State sync-back from a detached worktree: fast-forwarding the primary
  checkout, stale-worktree step/status regressions, union-merge files with no
  local branch commit (v1: #500, #508, `419dcdff`).
- Dirty-worktree teardown and crash-orphan reaping (v1: left-for-recovery
  heuristics, 24h age gate).
- Auto-persisting committed-but-unpushed product code before teardown (v1:
  never finished — `auto-persist-dirty-launch-worktrees-to-pushed-bran` was
  still open at removal time).
- `direct/body` workflows stranding product commits on the throwaway checkout
  (v1: #528; the detection guard `stranded_product_paths` was kept).

Starting points: PR #547 (what was removed and what was deliberately kept),
the deleted `# --- per-launch worktree isolation ---` section of `git.py` and
`_enter/_cleanup_launch_worktree` in `commands/launch.py` (recoverable from
git history at tag/commit `cb555c9e^` context), and the two never-merged fix
attempts, whose branches were deleted in the 2026-07-14 housekeeping — commits
recoverable by SHA: `fix-done-sentinel-worktree-drift` @ `fb79d3f9` (2 commits),
`fix/ff-primary-checkout-after-worktree-sync` @ `56c46890` (1 commit).

## Context

Until this ships, the re-accepted limitation is documented in the `coga/sync`
context: concurrent launches in one clone share an index/stash stack; run
concurrent sessions from separate clones/worktrees or sequentially
(`coga megalaunch` is strictly sequential and unaffected).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
