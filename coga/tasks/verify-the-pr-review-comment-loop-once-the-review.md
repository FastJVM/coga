---
slug: verify-the-pr-review-comment-loop-once-the-review
title: Verify the PR review-comment loop once the review queue drains
status: blocked
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
step: 1 (execute)
---

## Description

Verification-only ticket. Runs as a single `direct/body` step: this body is the
spec, and its phases execute in order.

### Phase 0 — precondition gate (run first, stop if it fails)

**Do not start phases 1–4 until the `code/with-review` review queue has
drained.** This ticket exists to check the *steady state*; running it against a
live backlog measures the backlog instead and produces a false result.

Run the check:

```
grep -rn '^step: .*(review)$' coga/tasks/*.md coga/tasks/*/ticket.md
```

The gate is satisfied when that returns **no rows** whose ticket status is
`active`, `in_progress`, `blocked`, or `paused` — i.e. no live ticket is parked
on a review step. (Two were parked when this gate was written:
`put-build-back` on `step: 4 (review)` and `recurring-recipe-question` on
`step: 5 (review)`. Both must be closed out or moved off review first.)

If the gate is **not** satisfied: record the current queue in the blackboard,
stop, and escalate per launch mode — ask the attending human, or `coga block`
with the remaining tickets named as the reason. Do not proceed to phase 1, and
do not mark the ticket done.

If the gate **is** satisfied: note in the blackboard which tickets retired since
2026-08-17 (that set is the input to phase 2), then continue.

### Phases 1–4 — the verification

Once phase 0 passes, verify four things about the review-comment loop and
record the result:

1. **Merged PRs actually close their tickets.** `coga autoclose` (or the
   `autoclose-merged` sweep) bumps every ticket whose `## Dev` `pr:` has
   merged. Snapshot below shows six merged PRs whose tickets were still
   `in_progress` on step 4 — confirm that backlog cannot recur, or that the
   sweep simply had not run yet.
2. **No review thread was merged unaddressed.** For each ticket retired since
   this ticket was written, check its PR for `isResolved: false` threads that
   got no reply and no code change. One dropped comment is already recorded
   below (PR 696).
3. **Newly frozen `review` steps carry `code/address-pr-comments`.** Note that
   phase 0 guarantees no ticket is *currently* parked on a review step, so
   checking live review steps would be vacuous. Check the frozen snapshots
   instead: for every ticket created since 2026-08-17 that carries a
   `code/with-review` snapshot, confirm its `review` step lists
   `code/address-pr-comments` rather than `skills: []`. Two tickets had the
   empty shape when this was written (#698 — snapshots freeze at creation and
   never refresh), so the assist path composed no skill layer for them. The
   question is whether that population has fully aged out, or whether new
   tickets are still freezing empty.
4. **Decide whether the loop needs a trigger at all.** Today nothing fetches
   review comments: the `review` step is `assignee: owner`, so the launch
   supervisor stops, megalaunch reports `skipped-human-gate`, and no core code
   polls `reviewThreads`. That may be correct (the owner gate is deliberate) or
   it may be the gap that let PR 696 through. This ticket only has to reach a
   decision and write it down — not implement one.

Scope note: this is verification, not a fix. If it finds a real defect, open a
separate ticket for the fix rather than growing this one.

## Context

Findings from a `bootstrap/orient` session on 2026-08-17. All evidence below is
a point-in-time snapshot to compare against, not a live claim.

**Why comments are not processed today.** `code/with-review` step 4 is:

```yaml
- name: review
  assignee: owner
  skills:
    - code/address-pr-comments
```

The skill exists and is current in the installed package (coga 0.3.0, uv tool
install). It is an *on-demand assist only* — its own opening line requires the
human to have explicitly run `coga launch <slug> --agent <type>`. Because the
step is `assignee: owner`, the launch supervisor stops at the handoff,
megalaunch skips it as `skipped-human-gate`, and the recurring sweep never
touches it. `grep -rn "reviewThread" src/coga/` returns zero hits: the only
GitHub-polling job is `autoclose`, which reads merged state, never comments.
The skill also deliberately never resolves threads and never bumps — resolution
and merge stay with the owner.

**Snapshot: six tickets on step 4 (review), all six PRs already merged.**

| ticket | PR | frozen `review` skills | unresolved threads |
| --- | --- | --- | --- |
| `remove-coga-build-and-project` | 691 | `[]` | 0 |
| `remove-legacy-config-compatibility-shims` | 692 | `code/address-pr-comments` | 1 |
| `refuse-recurring-runs-from-a-non-control-branch` | 693 | `code/address-pr-comments` | 0 |
| `autoclose-should-name-the-retire-follow-up` | 694 | `code/address-pr-comments` | 0 |
| `review-slack-channels` | 696 | `code/address-pr-comments` | 1 |
| `recurring-last-serviced-period-compares-as-a-strin` | 697 | `[]` | 0 |

The two `skills: []` rows are the frozen-snapshot behavior documented in #698 —
those tickets were created before the skill was added to the step definition,
and a frozen snapshot never refreshes.

**The two open threads.**

- PR 692, `src/coga/cli.py` (outdated) — codex-connector, "Let init bypass
  invalid aliases". Already answered: nicktoper replied that it was addressed
  in `b4cb5911` with regressions and a passing suite. Unresolved is expected
  here; only the human resolves threads.
- PR 696, `src/coga/resources/templates/coga/coga.toml:89`, **not outdated, no
  reply** — codex-connector, "Mirror the important webhook in the seeded
  example": enabling Slack from `example/coga/coga.toml` configures only the
  primary `webhook`, so a recipe failure or no-digest recurring error sends
  with `important=True` and exits because no important destination exists.
  This one merged genuinely unaddressed and is the concrete miss to check
  against.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run 2026-08-20 — phase 0 gate FAILED, stopped before phase 1

Ran the gate check verbatim:

```
grep -rn '^step: .*(review)$' coga/tasks/*.md coga/tasks/*/ticket.md
```

Four rows, **all `status: in_progress`** — so the gate is not satisfied. The two
named in the body (`put-build-back`, `recurring-recipe-question`) are still
parked, and two more have arrived since the gate was written.

| ticket | step | status | PR | PR state |
| --- | --- | --- | --- | --- |
| `put-build-back` | 4 (review) | in_progress | 701 | OPEN |
| `recurring-recipe-question` | 5 (review) | in_progress | 700 | OPEN |
| `validate-drift-classifier-misses-17-emitted-kinds` | 4 (review) | in_progress | 702 | OPEN |
| `dream-phases-2-3-cannot-complete-scan-subagents-re` | 4 (review) | in_progress | 703 | OPEN |

All four PRs are **open, none merged** (`gh pr view <n> --json state,mergedAt`),
so the queue has not merely gone un-swept — the reviews themselves are
outstanding. Draining requires the owner to review and merge 700–703, then let
`autoclose` (or a bump) move the tickets off review.

Per the body's phase 0 rule this run does **not** proceed to phases 1–4 and does
**not** mark the ticket done: measuring now would measure the live backlog, not
the steady state. Blocking with the four tickets named.

Nothing else was investigated this run, so phases 1–4 start from a clean slate
on relaunch. The 2026-08-17 snapshot in `## Context` is still the baseline; the
retired-since set for phase 2 must be recomputed at that time, and it will
include whichever of these four land in the meantime.

## Run 2026-08-26 — original blocker resolved, phase 0 gate still FAILED

Cleared the 2026-08-20 blocker after verifying that PRs 700–703 all merged on
2026-08-21 and all four named tickets are now `done` and off review.

Then reran the phase 0 gate verbatim. Three newer tickets are live on a review
step:

| ticket | step | status | PR | PR state |
| --- | --- | --- | --- | --- |
| `fix-the-autofix-analyst` | 4 (review) | in_progress | 724 | MERGED |
| `reconcile-recurring-wrapper-tty-admission-guidance` | 4 (review) | in_progress | 723 | MERGED |
| `rewrite-coga-base-prompt-and-agent-mode-block` | 4 (review) | in_progress | 726 | OPEN |

The first two show merged work still awaiting the autoclose/bump transition;
the third is an outstanding human review. The steady-state gate therefore
remains unsatisfied. Per phase 0, phases 1–4 were not started. On relaunch,
rerun the gate and recompute the retired-since-2026-08-17 set only after it
returns no live review tickets.

---

## Blockers

- [x] [2026-08-20 11:24] [agent:claude] id=20260820T112458 Phase 0 precondition gate failed: four tickets are still in_progress on a code/with-review review step, with all four PRs still OPEN (unmerged) — coga/tasks/put-build-back.md (step 4, PR 701), coga/tasks/recurring-recipe-question.md (step 5, PR 700), coga/tasks/validate-drift-classifier-misses-17-emitted-kinds.md (step 4, PR 702), coga/tasks/dream-phases-2-3-cannot-complete-scan-subagents-re.md (step 4, PR 703). The ticket body forbids running phases 1-4 against a live backlog. Need the owner to review and merge PRs 700-703 (or move those tickets off review), then relaunch this ticket.
  resolved: [2026-08-26 21:57] [human:nicktoper] Resolved: PRs 700-703 merged on 2026-08-21 and the four named tickets (put-build-back, recurring-recipe-question, validate-drift-classifier-misses-17-emitted-kinds, and dream-phases-2-3-cannot-complete-scan-subagents-re) are all now status done and off the review queue.

- [ ] [2026-08-26 21:58] [agent:claude] id=20260826T215802 Phase 0 precondition gate still fails: coga/tasks/fix-the-autofix-analyst.md is in_progress on review with merged PR 724; coga/tasks/reconcile-recurring-wrapper-tty-admission-guidance.md is in_progress on review with merged PR 723; and coga/tasks/rewrite-coga-base-prompt-and-agent-mode-block.md is in_progress on review with open PR 726. The first two need autoclose/bump and the third needs review/merge plus autoclose/bump before this steady-state verification can proceed.


---

## Blocker reminders

- 3023242c0745 last_reminded: 2026-08-21 11:54

- 3c1149d09e4e last_reminded: 2026-09-02 11:59
