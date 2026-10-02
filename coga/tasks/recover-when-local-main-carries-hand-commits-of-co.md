---
title: Recover when local main carries hand commits of coga state
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

When local main carries commits that touch only Coga state (`coga/tasks/**`, `coga/log.md`, `coga/recurring/**`) and are not on origin, Coga's publish can no longer fast-forward the control checkout. `fast_forward_control` (`src/coga/git.py`) prints a `git pull --rebase` note and `coga launch` refuses ("bringing this checkout to a clean 'main' at origin/main refused to change the checkout"). The operator's `git pull --rebase` then also fails, because the unpublished log lines Coga appended in the meantime leave `coga/log.md` dirty. Design and implement a guard so this state-only divergence repairs itself, or fails with one exact command that works, without ever discarding content that exists only locally. Respect the `coga/sync` contract (no committing on a local branch, stashing, or rebasing by Coga), or make the case to change it at the design gate.

Done when: a regression test reproduces the 2026-10-01 shape (a state-only local commit, a dirty `coga/log.md`, origin moved ahead) and `coga launch` either proceeds with main equal to origin and every local line preserved, or refuses with a message whose suggested command succeeds as-is. A local commit touching anything outside Coga state is still refused as today. The owning topic (`coga/sync` / `coga/internals/state-publication`) states the rule.

Incident (2026-10-01): an orient session (`94bb601e-cc9a-4e52-8e94-7c67ada785fb`) hand-committed `ec16e4e6c` ("Blackboard: …", 15:33) and `8222213ff` ("Ticket: … — workflow code/with-review", 16:00) for `marketing/fix-installer/offer-agent-cli-install-and-setup-at-init`. Meanwhile Coga published `b5e42a299` ("Sync coga state before launch") and `5dc52845b` ("Log: bootstrap/orient") to origin. Launch refused, and `git pull --rebase` refused on the dirty log. The fix that worked was `git pull --rebase --autostash origin main` followed by `git push`. The rebase dropped `ec16e4e6c` as "patch contents already upstream", so one of the two commits was already redundant. Related: the draft `fix-coga-git-sync-failures-that-leave-main-diverge` (its item 3: fast-forward when local content already matches origin) covers divergence from *failed syncs*; this ticket covers divergence from *hand commits*. Coordinate so both share one guard rather than two. Prevention side: "Tell agents never to git-commit coga task and log state".

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
