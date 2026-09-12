---
title: Four parked tickets carry premises that have since inverted
status: in_progress
owner: nicktoper
agent: claude
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

## Triage session 2026-09-12 (attended)

Re-verified each inversion against current `main` before proposing a verdict.
Related tickets checked for overlap: `triage-the-v2-parking-area-empty-descriptions-prem`
is `canceled`; `adjudicate-parked-and-active-tickets-whose-premise` and
`adjudicate-the-eight-premise-dead-v2-drafts` are drafts that do not name #1, #2 or #4.
The eight-drafts ticket does name `dev-loop-git-hygiene` as "asserted with no recorded
evidence — find the evidence or downgrade"; the evidence below discharges that ask, so
the closing message must carry the pointers.

### Evidence

1. `v2/dream-recurring-persist-done-stop-inline-delete` — confirmed inverted. Period tasks
   live at `coga/tasks/recurring/<name>/` (live dirs: `autoclose-merged`, `blocker-reminders`,
   `digest`, `dream`); `coga/contexts/coga/period-task/SKILL.md` says the period is *not*
   in the slug and that the sweep get-or-creates the stable path, logging
   `created|reused <ref> for <period>` in `coga/log.md`. `_task_with_slug` and
   `_live_task_for_template` are still the dedup gates in `src/coga/recurring.py`
   (`scan_due`, `create_template`) — the ticket asks to delete them. `create_debug_run`,
   `_reap_debug_orphans`, `_finalize_debug_run` no longer exist (debug-run removal done).
   Sibling `dream-sweeps-done-recurring-period-tickets` does not exist in `coga/tasks/`.
   Subject (stop inline deletion, persist `done`) is solved by a different design.
   → **cancel**, reason names the shipped design.

2. `v2/automerge-ticket` — the workflow `code/optimistic-merge` and skill `code/merge-pr`
   were never built; the surfaces it mirrors still exist. Packaging claim is inverted:
   `src/coga/resources/templates/coga/bootstrap/workflows/code/` holds
   `design-then-implement.md`, `with-review.md`, `with-self-review.md`; `coga/workflows/code/`
   does not exist. Per `coga/architecture`, a repo-local `workflows/<ref>.md` *overrides* the
   bundled `bootstrap/workflows/<ref>.md`, so following the ticket literally would put the
   new workflow in the override layer. Dead surfaces: `relay panic` → `coga block`,
   `relay slack` → `coga slack` (still the live path), `relay automerge` → the
   `autoclose` alias (`coga recurring launch autoclose-merged`), `relay-os/skills/…` →
   packaged `bootstrap/skills/…`. The recorded evaluator "correct and verified" is stale.
   Passes both README premise questions (subject not gone) → **rewrite down to the
   residual delta** if the owner still wants an optimistic-merge workflow; else cancel.

3. `v2/dev-loop-git-hygiene-lift-sync-with-main-into-code` — both halves shipped. Change 1:
   `coga/skills/code/implement/SKILL.md` step 8 "Freshen against `main` before handing off"
   (inherited by all three `code/*` workflows), and `coga open-pr`
   (`src/coga/open_pr.py`) refuses a branch with unsafe drift from `<remote>/<base>`.
   Change 2: `coga/workflows/branch-sweep/sweep.md` + `src/coga/branchsweep.py` +
   `src/coga/branchcleanup.py`. Status is `draft`, so `coga mark done` is not allowed
   directly (needs `mark active` first) → **close as already-satisfied**.
   Residue: `## pr` inline-body de-duplication in `with-self-review.md` — no ticket found
   on disk for the "dead inline body" issue Dream W36 raised (grep of `coga/tasks/*.md`
   hits only this ticket); note it in the closing message.

4. `verify-the-pr-review-comment-loop-once-the-review` — the description's "precondition
   now satisfied" is **no longer true**: the phase-0 gate (`grep '^step: .*(review)$'`)
   returns 10 rows today, all `in_progress`, with 7 open PRs (787–793). PR 761 (the open
   blocker's named ask) merged 2026-09-09. The blackboard's meta-finding stands: the
   zero-row gate has failed on four sampled dates. → owner decision: relax phase 0 (the
   phases are retrospective and do not need a quiet queue) and unblock, or cancel.

### Mechanics

Verdict application is CLI state (`coga mark canceled/active/done`, `coga unblock`) on
the control branch. The only PR-able work is ticket prose: the #2 rewrite and, if chosen,
the #4 phase-0 relaxation. `coga open-pr` treats ticket-body rewrites as publishable
(`_publishable_changes` in `src/coga/open_pr.py`), so that satisfies `requires: pr`.
