---
slug: verify-the-pr-review-comment-loop-once-the-review
title: Verify the PR review-comment loop once the review queue drains
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

Placeholder. Do not start this until the current `code/with-review` queue has
drained — every ticket now sitting on step 4 (review) is closed out, and the
`skills: []` frozen-snapshot population has aged out of the live set.

When that holds, verify four things about the review-comment loop and record
the result:

1. **Merged PRs actually close their tickets.** `coga autoclose` (or the
   `autoclose-merged` sweep) bumps every ticket whose `## Dev` `pr:` has
   merged. Snapshot below shows six merged PRs whose tickets were still
   `in_progress` on step 4 — confirm that backlog cannot recur, or that the
   sweep simply had not run yet.
2. **No review thread was merged unaddressed.** For each ticket retired since
   this ticket was written, check its PR for `isResolved: false` threads that
   got no reply and no code change. One dropped comment is already recorded
   below (PR 696).
3. **Every live `review` step carries `code/address-pr-comments`.** Grep the
   frozen `workflow:` snapshots of tickets on a review step for
   `skills: []`. Two tickets had that shape when this was written, so the
   assist path composed no skill layer for them.
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
