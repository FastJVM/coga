---
title: Launch moves the checkout to main before and after a ticket session
status: draft
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
---

## Description

Ticket launches (not bootstrap or chat targets) should bring the checkout to a clean, current main on their own before the agent starts, and again after the session ends, instead of relying on each agent to run the dev/checkouts start and end procedure. Today a session that ends on a feature branch (for example a bootstrap/orient chat) leaves the next launch starting there. Bootstrap and chat sessions may keep working from whatever branch they start on.

## Context

Requested by the owner in a `bootstrap/orient` chat (2026-09-25) after a
session started on a leftover `daily-autoclose-branches` checkout. #896
(`stop-using-worktrees`) put a start/work/end rule in `dev/checkouts`, but
the agent performs it, and only code steps follow it.

Proposed behavior (to be refined by the design step):

- **Before the agent starts** (ticket targets only; `bootstrap/*` targets
  skip it): `git fetch origin main`; if HEAD is another branch with a clean
  tree, `git switch main`; discard dirty Coga state paths (`coga/tasks/`,
  `coga/log.md`, `coga/recurring/`) only when their bytes equal
  `origin/main` (the `dev/checkouts` end rule); `git merge --ff-only
  origin/main`. Anything else (other dirty paths, unpublished Coga state,
  a diverged `main`) makes the launch refuse loudly without changing the
  checkout.
- **After the session ends:** run the same routine as a backup so the
  checkout is back on `main`. If it can't clean safely, report that loudly
  without making the finished step count as failed.

Design points found while evaluating:

- **Ordering:** the move to `main` must happen before the ticket is read
  and the prompt is composed, or the prompt comes from the branch's files.
  Resolve the target, move to `main`, reload config, resolve again.
- **Chained steps:** it must run before every step that the `coga launch`
  supervisor chains, not only the first.
- **Existing exceptions:** keep the legacy assist-checkout path
  (`address-pr-comments` in a recorded `worktree:` on `branch:`,
  `commands/launch.py` near `candidate_assist_branch`) and never touch a
  `/tmp` sandbox clone.
- **Existing gates:** reconcile with `_refuse_non_control_branch` /
  `_sync_control_checkout_ahead` (`recurring_runner.py`), which launch
  already uses for `recurring/` targets.
- **One owner:** `dev/checkouts` should say launch performs the start and
  end moves. Agents only confirm they are on `main`, and step skills
  (`code/implement`, `self-qa`, `open-pr`, `address-pr-comments`) and
  `coga/internals/agent-spawn` stop restating the procedure. Update the
  packaged copies of those docs to match.
- **Principles:** launch starts switching branches and discarding files, a
  change from "launch never chooses a working directory". Keep that
  confined to the cases above, which lose no work.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
