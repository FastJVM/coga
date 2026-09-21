---
title: Document how to recover a retired ticket's body from git, including pre-rename
  paths
status: draft
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
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `gap` findings with no open owner. Two findings about the same missing recipe: how to read a retired/deleted ticket's body back from git, including tickets deleted before the `relay-os/` → `coga/` rename, which a `coga/tasks/`-scoped history search silently misses. Decide the owning surface (the recovery recipe in `coga/tasks/v2/README.md`, `coga/architecture`, and/or `bootstrap/ticket`'s citation guidance) and add it once.

**F36 — No context or skill says how to read a retired ticket's body back from Git**  
(Dream 2026-W39 Phase 2, shard ks-19; class `gap`; target `coga/contexts/coga/architecture/SKILL.md`)

Tickets repeatedly need the body of a ticket that `coga retire` (or an older cleanup) already deleted, and each rediscovers the recipe on its own: `triage-five-review-comments-that-merged-unanswered` (done) was told "recover the source ticket from Git history if it has been retired" and used `git show 6c305673^:coga/tasks/verify-the-pr-review-comment-loop-once-the-review.md`; `the-ticket-interview-never-asks-what-done-means` (in_progress) records "the file was deleted in `ffb0a383` — it is not on disk. Recovered at design time with `git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md`"; `adjudicate-parked-and-active-tickets-whose-premise` (done) notes wording "reachable only through git history" and had to recover accepted interview prompts the same way. The only written recipe is in `coga/tasks/v2/README.md` (`git log --all --diff-filter=D --name-only -- 'coga/tasks/<slug>*'` to find the deleting commit, then `git show <commit>^:<path>`), scoped to the parked-draft premise check — it is not a context or skill and does not compose into launch prompts for ordinary tickets. The closest knowledge text, `coga/contexts/coga/architecture/SKILL.md` (~line 41, "renaming a task orphans its whole prior history under the retired tag ... grep the retired tag when reconstructing the trail"), covers only the `coga/log.md` trail, not the deleted ticket file; `dev/code` "Who retires the checkout" says retire acts "at the lifecycle event where the ticket still exists" without saying where the body goes afterwards. Grep of `coga/contexts/**/SKILL.md` and repo-authored `coga/skills/**` for `git show`/`--diff-filter=D`/"recover" against tasks found no such guidance. Proposed: one sentence plus the two-command recipe beside the architecture context's retired-tag passage (or in `dev/code` next to "Who retires the checkout"), stating that a retired ticket's body and blackboard survive only as a Git blob, that `coga show <slug>` will not find it, and that the `v2/README.md` premise check should link to that owner rather than restate it. No open ticket owns this: task-title grep for retired/recover/git-history found only `preserve-edits-during-released-claim-recovery`, which is unrelated (launch admission).

**F43 — Ticket-history recovery recipe misses tickets deleted before the `relay-os` → `coga` rename**  
(Dream 2026-W39 Phase 2, shard ks-22; class `gap`; target `coga/tasks/v2/README.md (the `git log --all --diff-filter=D --name-only -- 'coga/tasks/<slug>*'` recovery recipe; same gap in `bootstrap/ticket`'s citation guidance)`)

Two independent tickets rediscovered that the task tree was `relay-os/tasks/` before commit `d0645a197` ("Rename relay to coga (full rebrand)", PR #454), so any history search scoped to `coga/tasks/` silently misses tickets deleted before the rename. `coga/tasks/adjudicate-the-eight-premise-dead-v2-drafts.md` (Context, "Recoverable autotrigger background") found six of seven cited slugs absent until it searched the old path: "The four retired hazard tickets were deleted under `relay-os/tasks/`, so searching only `coga/tasks/` history misses them. All four source bodies were recovered with `git show <deletion>^:relay-os/tasks/<slug>/ticket.md`" (commits `d7086ecd`, `078dd705`, `2584de1d`, `c008c23b`). `coga/tasks/simplify-ticket-format.md` (Context, line ~540) independently had to run its `watchers` history search "under both `coga/tasks/` and the former `relay-os/tasks/`". `coga/tasks/v2/README.md` lines 76-78 carry the only written recipe for recovering a dangling citation and it names only `'coga/tasks/<slug>*'`; `docs/migrating-to-coga.md` records the rename for operators but says nothing about history recovery, and no context or skill under `coga/contexts/`, `coga/skills/coga`, `coga/skills/code`, or `coga/skills/bootstrap` mentions `relay-os/tasks` at all (grep empty). Proposed change: extend the README recipe (and the `bootstrap/ticket` citation guidance that points to it) with one sentence — search both pathspecs, e.g. `-- 'coga/tasks/<slug>*' 'relay-os/tasks/<slug>*'`, because deletions before `d0645a197` live under the old tree. Owner search: grep of every task file for `pre-rename`/`relay-os/tasks` finds only historical mentions (`launch-activates-before-preflight` done, `four-parked-tickets-carry-premises-that-have-since` done, `no-durable-runbook-covers-running-coga-headless` canceled); no open ticket proposes fixing the recipe, and the in_progress `adjudicate-the-eight-premise-dead-v2-drafts` only inlines the recovered bodies into the autotrigger draft, not the README.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
