---
title: Decide the fate of the multiply-probe-harness worktree evidence
status: draft
owner: nicktoper
workflow: null
---

## Description

The worktree /home/n/Code/claude/multiply-probe-harness (380M: branch codex/multiply-probe-harness at f51f7629, PR #13 merged with HEAD=prhead) was held back from the worktree cleanup (clean-up-all-the-working-trees, item O1). Its gitignored probes/local/20260821T185147Z/ (142M, 16 nested fixture repos) is the interactive-probe run evidence cited by multiply's done ticket v1/1b-lifecycle-experiments. Investigate whether that evidence is still needed, and whether any of it should be preserved durably (for example summarized into the ticket or kept elsewhere), before the worktree is removed. Its .git back-link is broken: it points at the nonexistent claude/multiply/.git/worktrees/..., but the worktree is registered in codex/multiply. Removal therefore needs 'git -C /home/n/Code/codex/multiply worktree repair /home/n/Code/claude/multiply-probe-harness' followed by a normal 'git worktree remove' (no --force). The same question applies to the retained probe-evidence worktrees codex/multiply-startup-upgrade-probe, codex/multiply-debug-platform-contract, and multiply-harness-evidence (~9G together); see that ticket's blackboard.

## Context

Resolved 2026-10-23 in an attended session. When checked, all four worktrees were
already in the desktop Trash: `multiply-probe-harness` (380M, moved there 2026-09-30),
plus `multiply-harness-evidence` (2.6G), `multiply-startup-upgrade-probe` (4.3G) and
`multiply-debug-platform-contract` (2.2G), all moved there 2026-09-24. `codex/multiply`
no longer registered them, so the repair/remove recipe above was moot.

Why none of the evidence needed preserving:
- The citing ticket `v1/1b-lifecycle-experiments` was deleted from multiply (`ae149cb8`, then retired).
- No file on multiply `main` references run `20260821T185147Z` or these paths as evidence.
- multiply's `probes/evidence/README.md` makes raw `probes/local/` data disposable by design;
  the bounded summaries (E0–E18, `debug-platform-contract-linux.md`) are committed on `main`.
- All four branches merged: multiply PRs #13, #65, #99 and #90.

The owner approved permanent deletion; the four directories and their `.trashinfo` files
were removed from `~/.local/share/Trash` and verified gone.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
