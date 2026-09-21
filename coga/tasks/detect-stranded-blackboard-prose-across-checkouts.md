---
title: Detect stranded blackboard prose across checkouts
status: draft
owner: nicktoper
workflow: null
---

## Description

Residual 1 of detect-stranded-ticket-writes-across-checkouts, spun back to a draft per that ticket's stated fallback and the owner's 2026-09-09 steer. That ticket shipped the committed-duplicate half: github_preflight.stranded_task_state_paths compares the recorded branch against control inside one repository, coga open-pr words its freshness refusal as a stranded ticket write, and coga bump warns one step earlier. What remains is stranded blackboard *prose* — working memory written in the feature checkout's ticket copy and never committed or synced anywhere — which no ref comparison can see. Before designing, read that ticket's '### Out of scope' section: the primary-copy failure mode (a missing '## Dev') is already refused by the 'requires: branch' gate; a general comparator would have to clear the missing-worktree-pointer case, the invisible independent /tmp clone, the detached mid-rebase worktree, and the fact that control-ahead divergence is the normal state, for a rare and low-stakes case. If revived, the discriminator worth keeping is one-directional content the other copy lacks, and the comparison must stay report-only.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
