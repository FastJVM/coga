---
slug: four-parked-tickets-carry-premises-that-have-since
title: Four parked tickets carry premises that have since inverted
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 1 (implement)
---

## Description

Four tickets describe a repo that no longer exists. Each reads as authoritative to whoever
picks it up, and three of them are pre-rename throughout (`relay-os/`, `src/relay/`,
`relay <verb>`).

Deliverable per ticket is a decision — cancel, rewrite down to the residual delta, or
unblock — not an implementation. That is why this is one triage ticket rather than four
work tickets.

1. `coga/tasks/v2/dream-recurring-persist-done-stop-inline-delete.md` (paused)
2. `coga/tasks/v2/automerge-ticket.md` (paused)
3. `coga/tasks/v2/dev-loop-git-hygiene-lift-sync-with-main-into-code.md` (draft)
4. `coga/tasks/verify-the-pr-review-comment-loop-once-the-review.md`

Related but **separate**: `coga/tasks/triage-the-v2-parking-area-empty-descriptions-prem.md`
already owns the broader v2 sweep (empty descriptions, premise-dead drafts, the README
table). These four are named individually because Dream verified each one's inversion
against current code; if that ticket is being worked, fold these in as evidence rather than
running both.

## Context

Citations name symbols and files, not line numbers.

**1. `v2/dream-recurring-persist-done-stop-inline-delete`** — paused since 2026-06-08, and
every load-bearing assumption is now false. It specifies flat `recurring-<name>-<period>`
task slugs with the period encoded in the slug; an enqueue pass that "derives a firing date
from the slug's period key"; removal of `_task_with_slug`/`_live_task_for_template` so
creation "never dedupes" and suffixes colliding slugs `-2`; and it lists "grouping period
tickets under a `tasks/recurring/` subdirectory" as explicitly **out of scope**. Shipped
reality is the opposite on all four: period tasks live at the stable path
`coga/tasks/recurring/<name>/` with slug `recurring/<name>` and the period deliberately not
in the slug (`coga/contexts/coga/period-task/SKILL.md`), and the recurring context documents
the sweep as *get-or-creating* that stable task and recording the period as a
`created|reused <task-ref> for <period>` line in `coga/log.md`. Its stage-3 sibling
`dream-sweeps-done-recurring-period-tickets` no longer exists, Dream's reap is live, and the
debug-run removal it asks for is already done. It also contains 23 occurrences of the old
product name.

**2. `v2/automerge-ticket`** — its `## Scope` states, and its `## Evaluator review`
explicitly **re-verified** ("correct and verified"), that "the `code/` workflow namespace is
not shipped in the packaged template, so no dual-copy sync is required". The layout is now
exactly inverted: `src/coga/resources/templates/coga/bootstrap/workflows/code/` holds
`design-then-implement.md`, `with-review.md` and `with-self-review.md`, while the live tree
has **no** `coga/workflows/code/` directory. An implementer following the ticket would
create `coga/workflows/code/optimistic-merge.md`, which under local-first resolution sits in
the override layer rather than beside the three workflows it is told to mirror — and the
"no sync needed" note would be wrong for the wrong reason. The rest is pre-rename
throughout. **The recorded evaluator verification is what makes this dangerous**: it reads
as settled.

**3. `v2/dev-loop-git-hygiene-lift-sync-with-main-into-code`** — both halves of its
`## Acceptance` already shipped. Change 1 (lift sync-with-`main` out of
`with-self-review.md`'s `## pr` body into the shared PR skill so all three dev workflows
inherit it): `coga/skills/code/implement/SKILL.md` step 8 "Freshen against `main` before
handing off" now carries it for every workflow that uses `code/implement` — all three do —
and `coga open-pr` itself refuses a branch with unsafe material drift from
`<remote>/<base>`. Change 2 (a recurring merged-branch/worktree cleanup gated to
provably-merged branches): that is `coga/workflows/branch-sweep/sweep.md` plus
`src/coga/branchsweep.py` and `src/coga/branchcleanup.py`, which skip the configured control
branch, the checked-out branch, and any branch recorded on a non-terminal ticket, and report
`skipped-worktree-pinned` rather than deleting a branch a live worktree holds. Also
pre-rename throughout. Likely outcome: close as already-satisfied. Any residue is the `## pr`
de-duplication, which Dream 2026-W36 raised separately as the dead-inline-body issue in the
shipped `code/*` workflows.

**4. `verify-the-pr-review-comment-loop-once-the-review`** — blocked on a precondition
("once the review queue drains") that is now satisfied; only two PRs are open. This one is a
lifecycle decision (`coga unblock` / relaunch), not a rewrite, and needs the owner.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shards `ks-03`, `ks-10`), classified
`stale` against ticket files rather than contract surface — which is why they route here
instead of to a proposal PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
