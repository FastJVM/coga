---
title: Verify the PR review-comment loop once the review queue drains
status: done
owner: nicktoper
agent: claude
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
---

## Description

Verification-only ticket. Runs as a single `direct/body` step: this body is the
spec, and its phases execute in order.

### Phase 0 — measurement window (record, do not gate)

**Reshaped 2026-09-13 by owner decision** (see the resolved blocker on the
blackboard). The original phase 0 required the `code/with-review` review queue
to return zero live rows before phases 1–4 could start. Four samples over four
weeks (2026-08-20, 08-26, 09-09, 09-13) each found a different set of tickets
parked on review — normal throughput keeps at least one PR in owner review at
every instant — so the zero-row state never occurs and the ticket could not
run. Phases 1–4 are all retrospective (they read *retired* tickets and *merged*
PRs), so they never needed a quiet queue.

The measurement window is **closed: tickets retired between 2026-08-17 and
2026-09-13 inclusive.** Phases 1–4 read only that population. Tickets whose
PR is still open, or that retired after the window, are out of scope for this
run.

Run the queue check anyway and record the result on the blackboard as an
observation, not a gate:

```
grep -rn '^step: .*(review)$' coga/tasks/*.md coga/tasks/*/ticket.md
```

For each live row note the PR state. Rows whose PR has **merged** but whose
ticket is still `in_progress` on review are phase 1 evidence (a sweep that
has not run, or a sweep that cannot see them); rows whose PR is still open are
just the live backlog and are not measured.

Then list on the blackboard the tickets retired inside the window (that set is
the input to phases 2 and 3) and continue to phase 1.

### Phases 1–4 — the verification

With the window fixed by phase 0, verify four things about the review-comment loop and
record the result:

1. **Merged PRs actually close their tickets.** `coga autoclose` (or the
   `autoclose-merged` sweep) bumps every ticket whose `## Dev` `pr:` has
   merged. Snapshot below shows six merged PRs whose tickets were still
   `in_progress` on step 4 — confirm that backlog cannot recur, or that the
   sweep simply had not run yet.
2. **No review thread was merged unaddressed.** For each ticket retired inside
   the window, check its PR for `isResolved: false` threads that
   got no reply and no code change. One dropped comment is already recorded
   below (PR 696).
3. **Newly frozen `review` steps carry `code/address-pr-comments`.** Live
   review steps are a moving sample, so check the frozen snapshots instead:
   for every ticket created inside the window that carries a
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

## Run 2026-09-09 — 2026-08-26 blocker resolved, phase 0 gate FAILED again (3rd time)

Cleared the 2026-08-26 ask: all three named tickets are now `done` and off review
(`fix-the-autofix-analyst` PR 724, `reconcile-recurring-wrapper-tty-admission-guidance`
PR 723, `rewrite-coga-base-prompt-and-agent-mode-block` PR 726 — all merged).

Reran the gate verbatim. One live row:

| ticket | step | status | PR | PR state |
| --- | --- | --- | --- | --- |
| `a-slack-repo-without-important-webhook-can-abort-t` | 4 (review) | in_progress | 761 | OPEN (created 2026-09-08, no reviewDecision) |

Not a missed sweep — the PR is a day old and genuinely awaiting owner review.
Per phase 0, phases 1–4 were not started and the ticket is not marked done.

Note: this ticket carries a `code/address-pr-comments` review step, so it is *not*
another instance of the frozen-empty-skills shape from phase 3. It is also, by
subject, the fix for the PR 696 miss recorded in `## Context` — phase 2's concrete
example now has a remediation ticket in flight.

### Meta-finding: the gate may be unsatisfiable as written

Three attempts (2026-08-20, 2026-08-26, 2026-09-09) over three weeks, three failures,
with a *different* set of tickets parked on review each time. The queue drains
continuously but is never empty at any sampled instant, because normal throughput
keeps at least one PR in owner review. Waiting for a zero-row gate is waiting for a
quiet period the repo does not appear to have.

This is a ticket-shape problem, not something to route around, so it goes to the owner
rather than being self-resolved. The cheap fix if the owner agrees: phases 1–4 are all
retrospective — they read *retired* tickets and *merged* PRs — so they do not actually
need a quiet queue. Only phase 3's original "check live review steps" framing did, and
the body already replaced that with a frozen-snapshot check. Relaxing phase 0 to
"exclude tickets whose PR opened after the measurement window" (or dropping the gate and
scoping phases 1–4 to tickets retired in a closed date range) would make the ticket
runnable without measuring the live backlog. Naming that option in the blocker.

Phases 1–4 still start from a clean slate on relaunch; the retired-since-2026-08-17 set
must be recomputed then.

---

## Run 2026-09-13 — blocker resolved with owner, gate reshaped, phases 1–4 COMPLETE

**Blocker resolution.** PR 761 merged 2026-09-09; its ticket is `done`. The
shape question went to the owner in-session (blocker-resolution exception);
decision: **closed measurement window, run now**. Phase 0 rewritten in the body
as a window (tickets retired 2026-08-17 → 2026-09-13 inclusive, 38 tickets via
`auto-bumped on merge of PR #N → done` in `coga/log.md`), with the live queue
recorded as an observation only. Log timestamps are local (UTC−7); GitHub
`mergedAt` is UTC — all lags below are corrected.

### Phase 0 observation — live queue at 2026-09-13

12 tickets on a review step, the most any of the four samples found. PRs
784/785/786 merged 2026-09-11 ~19:00Z, two hours *after* the last sweep run
(09-11 10:00 local = 17:00Z); the sweep has not fired since. PRs 787–795 are
open, opened 09-11 → 09-13, awaiting owner review. None measured.

### Phase 1 — merged PRs do close their tickets; the backlog is scheduler downtime

- 38/38 in-window merged PRs were auto-bumped to `done`. **0 of 38 survived a
  sweep run**: every ticket closed on the first `autoclose-merged` run after
  its merge (PR 701: 6 min).
- Corrected merge→close lag: median ≈ 23 h, max ≈ 150 h (PRs 723/724, merged
  08-26, closed 09-01). All long lags are days on which the sweep did not run.
- The sweep is `schedule: "0 8 * * *"` but is fired by an operator-owned
  scheduler outside Coga (`coga/contexts/coga/recurring`); it ran on 13 of the
  window's 28 days (08-17,18,19,21,24,25; 09-02,03,04,08,09,10,11). Gaps:
  08-20, 08-22/23, 08-26→09-01, 09-05→07, 09-12→13.
- **Verdict:** the 2026-08-17 six-row snapshot was "the sweep had not run yet",
  and that *can* recur every time the external scheduler misses a day. The
  sweep itself has no defect. Not a loop bug; the gap is that the queue check
  in this ticket counted merged-but-unswept rows as backlog.

### Phase 2 — 7 of 38 merged PRs carried an unanswered review thread

Queried `reviewThreads` on all 38 PRs: 17 unresolved threads. 10 had an owner
reply (692, 723, 724, 726×5, 758, 759 — "unresolved" only means nobody clicked
resolve; skill and owner both deliberately never resolve). **7 bot threads had
no reply, were not outdated (no code change at the flagged line), and merged
as-is: PRs 696, 699 (P1), 704, 705, 706, 747, 755.** That is 18% of merged
PRs. Checked each against today's tree:

| PR | thread | state today |
| --- | --- | --- |
| 696 | mirror important webhook in seeded example | fixed out-of-band by `a-slack-repo-without-important-webhook-can-abort-t` (PR 761) — found by an orient session, not by the loop |
| 699 | P1: revalidate control before trusting pre-scan ledger | still as written (`_LEDGER_LOADED = "yes"` set unconditionally under `control_is_fresh`) |
| 704 | reject context symlinks escaping the checkout | still as written (`path.is_file() or path.is_symlink()`) |
| 705 | attribute shim completions to `system` | **confirmed live**: `recurring/autoclose-merged` completions log as `[human:nicktoper] task done` (09-10, 09-11) |
| 706 | metrics parser for annotated PR lines | overtaken incidentally: `scripts/human_minutes.py` PR regex rewritten by PR 784 |
| 747 | recheck released witness before overwriting | still as written (`FileMutationRollback.capture` after the control fetch) |
| 755 | keep superseded designs out of the launch blackboard | still as written (`dev/code` moves them below the fence) |

Five standing comments handed to a human via draft
`triage-five-review-comments-that-merged-unanswered` (brief-for-human).

### Phase 3 — frozen snapshots are all correct; the empty population aged out

113 tickets created in the window; 55 carry a frozen `code/with-review`
snapshot (48 live files, 7 read from git for Dream-reaped tickets). **55/55
freeze `code/address-pr-comments` on `review`; 0 empty.** The only
`skills: []` tickets ever seen were 691 and 697, created before 08-17 and
retired 08-18. #698's frozen-snapshot behavior is real but has no remaining
population. Side-check: `code/design-then-implement` and `code/with-self-review`
also carry the skill on `review`; `docs/with-review` does not (no PR artifact
expected there — noted, not measured).

### Phase 4 — decision

The assist skill (`code/address-pr-comments`) was launched **once** in four
weeks (`simplify-ticket-format`, 09-10) against ~40 owner reviews. Phase 3
shows the skill is always available; phase 2 shows it is almost never used and
that 18% of merges drop a bot comment. So the PR 696 miss was not the
frozen-snapshot bug and not a missing skill — it is that **nothing surfaces an
unanswered thread to the owner**, who merges from the GitHub UI where
unresolved threads do not block.

**Decision: keep the owner gate; add post-merge detection, not a new trigger.**
Merge and thread resolution stay human (deliberate, and the skill's own
contract). The lightest legible fix is in the one place that already touches
every merged PR: when the `autoclose-merged` sweep closes a ticket, fetch that
PR's `reviewThreads` once and name every unresolved, non-outdated,
reply-less thread in its summary and Slack line, exactly as it already names
the `coga retire` follow-up. Report-only: no resolving, no replying, no
auto-launch of the review step, no new poller. Fix ticket:
`autoclose-should-name-unanswered-review-threads-on` (draft, code/with-review).

Rejected: (a) auto-launching the assist on review entry — bot comments arrive
minutes after open-pr, but the owner gate exists so a human reads them first;
(b) a merge-blocking check — Coga does not own GitHub merge policy; (c) doing
nothing — 18% drop rate with a P1 among them is a real, recurring miss.

### Verification only — nothing fixed here

Two drafts opened per the scope note; no product code changed. `direct/body`
ticket, closing with `coga mark done`.

## Blockers

- [x] [2026-08-20 11:24] [agent:claude] id=20260820T112458 Phase 0 precondition gate failed: four tickets are still in_progress on a code/with-review review step, with all four PRs still OPEN (unmerged) — coga/tasks/put-build-back.md (step 4, PR 701), coga/tasks/recurring-recipe-question.md (step 5, PR 700), coga/tasks/validate-drift-classifier-misses-17-emitted-kinds.md (step 4, PR 702), coga/tasks/dream-phases-2-3-cannot-complete-scan-subagents-re.md (step 4, PR 703). The ticket body forbids running phases 1-4 against a live backlog. Need the owner to review and merge PRs 700-703 (or move those tickets off review), then relaunch this ticket.
  resolved: [2026-08-26 21:57] [human:nicktoper] Resolved: PRs 700-703 merged on 2026-08-21 and the four named tickets (put-build-back, recurring-recipe-question, validate-drift-classifier-misses-17-emitted-kinds, and dream-phases-2-3-cannot-complete-scan-subagents-re) are all now status done and off the review queue.

- [x] [2026-08-26 21:58] [agent:claude] id=20260826T215802 Phase 0 precondition gate still fails: coga/tasks/fix-the-autofix-analyst.md is in_progress on review with merged PR 724; coga/tasks/reconcile-recurring-wrapper-tty-admission-guidance.md is in_progress on review with merged PR 723; and coga/tasks/rewrite-coga-base-prompt-and-agent-mode-block.md is in_progress on review with open PR 726. The first two need autoclose/bump and the third needs review/merge plus autoclose/bump before this steady-state verification can proceed.
  resolved: [2026-09-09 12:07] [human:nicktoper] Resolved: all three named tickets are now status done and off the review queue — fix-the-autofix-analyst (PR 724 merged), reconcile-recurring-wrapper-tty-admission-guidance (PR 723 merged), and rewrite-coga-base-prompt-and-agent-mode-block (PR 726 merged). The autoclose/bump transitions the ask was waiting on have all landed.

- [x] [2026-09-09 12:08] [agent:claude] id=20260909T120805 Phase 0 precondition gate fails a third time: coga/tasks/a-slack-repo-without-important-webhook-can-abort-t.md is in_progress on step 4 (review) with PR 761 still OPEN and unreviewed (opened 2026-09-08). Needs owner review+merge, then autoclose/bump. But please also decide the shape question: three attempts over three weeks have each found a different ticket parked on review, so a zero-row queue may never occur. Phases 1-4 are all retrospective (they read retired tickets and merged PRs) and do not actually need a quiet queue — consider relaxing phase 0 to ignore tickets whose PR opened after the measurement window, or scoping phases 1-4 to a closed date range, so this verification can run at all.
  resolved: [2026-09-13 22:25] [human:nicktoper] Resolved 2026-09-13 with the owner. (1) PR 761 merged 2026-09-09 and a-slack-repo-without-important-webhook-can-abort-t is done. (2) Shape decision: phase 0 is no longer a zero-row gate. Four samples over four weeks never found an empty review queue (12 live rows today: PRs 784-786 merged but unswept, 787-795 open), and phases 1-4 are retrospective, so the body now fixes a closed measurement window - tickets retired 2026-08-17..2026-09-13 inclusive - and records the live queue as an observation only. Body rewritten accordingly; phases 1-4 run in this session.


---

## Blocker reminders

- 3023242c0745 last_reminded: 2026-08-21 11:54

- 3c1149d09e4e last_reminded: 2026-09-02 11:59

- 154e15295e36 last_reminded: 2026-09-11 10:00
