---
title: Decide the fate of the multiply-probe-harness worktree evidence
status: draft
owner: nicktoper
workflow: null
---

## Description

The worktree /home/n/Code/claude/multiply-probe-harness (380M: branch codex/multiply-probe-harness at f51f7629, PR #13 merged with HEAD=prhead) was held back from the worktree cleanup (clean-up-all-the-working-trees, item O1). Its gitignored probes/local/20260821T185147Z/ (142M, 16 nested fixture repos) is the interactive-probe run evidence cited by multiply's done ticket v1/1b-lifecycle-experiments. Investigate whether that evidence is still needed, and whether any of it should be preserved durably (for example summarized into the ticket or kept elsewhere), before the worktree is removed. Its .git back-link is broken: it points at the nonexistent claude/multiply/.git/worktrees/..., but the worktree is registered in codex/multiply. Removal therefore needs 'git -C /home/n/Code/codex/multiply worktree repair /home/n/Code/claude/multiply-probe-harness' followed by a normal 'git worktree remove' (no --force). The same question applies to the retained probe-evidence worktrees codex/multiply-startup-upgrade-probe, codex/multiply-debug-platform-contract, and multiply-harness-evidence (~9G together); see that ticket's blackboard.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
