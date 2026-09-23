---
title: Autofix dedupe ignores closed autofix tickets
status: draft
owner: nicktoper
contexts:
- coga/recurring
- coga/codebase
workflow: null
---

## Description

The autofix analyst decides whether a broken recurring run is already ticketed
from one list: the `autofix/` tickets `open_autofix_tickets` hands to
`build_prompt`. That function skips every ticket whose status is in
`TERMINAL_STATUSES` (`done`, `canceled`). So once an autofix ticket closes, the
same symptom coming back gets a brand-new ticket, diagnosed from scratch, with
no pointer to the earlier fix. The module docstring calls the loop
"repetition-aware" on the strength of that list, but it is repetition-aware
only while the earlier ticket is still open.

**Proposed fix direction** (a suggestion; the design call is yours): also list
*recently closed* `autofix/` tickets in the analyst prompt, marked closed, so
the analyst can either answer `duplicate` (the fix has not reached this run
yet) or file a `problem` that names the closed ticket as a possible regression.
Bound the list by recency or count so the prompt does not grow with the repo's
history.

What this would *not* cover, stated so nobody assumes it does:

- **Deleted tickets.** `retro/done-ticket` deletes every ticket it processes,
  and a deleted ticket is not in `list_tasks` at all. Its record is
  `coga/log.md` and git history. Either accept that gap explicitly, or read
  the log for recently created/closed `autofix/` slugs and their titles.
- **Cross-repo duplicates.** Each repo's analyst sees only its own
  `coga/tasks/autofix/`. A packaged template that breaks in two repos gets a
  ticket in each. That is a separate problem; see the evidence below.

Done looks like: a symptom whose autofix ticket closed within the bound gets a
`duplicate` verdict or a regression-flagged ticket that names the earlier slug,
covered in `tests/test_recurring_autofix.py`, and the docstring's
"repetition-aware" claim states what the list actually includes.

## Context

Reported from a downstream repo, `FastJVM/admin`, where the evidence lives.

- **Verified against `origin/main` on 2026-09-22 (`c2268b05`):**
  `recurring_autofix.open_autofix_tickets` does
  `if ticket.status in TERMINAL_STATUSES: continue`, and its result is the only
  "already ticketed" input `build_prompt` gives the analyst. The prompt text
  says "the autofix tickets that are already open", so the analyst is told
  nothing about closed ones.
- **The terminal-status case, observed.** The skill-update stale-lease failure
  was ticketed as `autofix/fix-skill-update-push-rejected-by-stale-force-with`
  (created 2026-08-31, fixed by FastJVM/coga#734, `done` 2026-09-01). The same
  symptom was ticketed again as
  `autofix/fix-skill-update-pr-push-failing-on-a-stale-force` (created
  2026-09-08, `done` 2026-09-11 via FastJVM/coga#760), diagnosed from
  scratch. Both still exist in `FastJVM/admin`'s `coga/tasks/autofix/`.
- **The cross-repo case, observed (not fixed by the proposal above).** The
  digest spool blank-line leak was ticketed in `FastJVM/admin` as
  `autofix/stop-the-digest-spool-leaking-a-blank-line-on-ever` (created
  2026-08-30; deleted in that repo's commit `1a4e13a6`) and, independently,
  here as `autofix/stop-the-digest-spool-drain-leaking-a-blank-line-e`
  (created 2026-09-04, closed 2026-09-18 as already satisfied by PR #786; see
  this repo's `coga/log.md`). Both ticket files are gone; cite them by slug
  plus log.
- `FastJVM/admin` works around this today with a manual four-place grep (its
  autofix tickets, its log and history, this repo's tasks and commits) as step
  1 of its autofix triage, in its local context `coga/upstream`. The grep over
  its own closed and deleted tickets stays needed until this ships and reaches
  that repo's installed checkout; the grep over this repo covers the
  cross-repo case and stays regardless.
- **Adjacent prior work, neither about dedupe:** `fix-the-autofix-analyst`
  (scoped stderr/stdout detail, stdin inheritance, an `[autofix] agent` key;
  closed without shipping them) and
  `the-autofix-analyst-ticket-closed-without-shipping` (which shipped those
  three). No existing ticket in `coga/tasks/` covers duplicate scope; the
  "already ticketed" hits elsewhere are Dream's phase-6 dedupe, a different
  mechanism.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
