---
title: Autoclose should name unanswered review threads on the PR it closes
status: in_progress
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
step: 2 (peer-review)
agent: claude
---

## Description

Follow-up from verify-the-pr-review-comment-loop-once-the-review (phase 4 decision, 2026-09-13). Between 2026-08-17 and 2026-09-13, 7 of 38 merged PRs (696, 699, 704, 705, 706, 747, 755) carried a bot review thread that was not outdated, got no reply, and had no code change before merge. Every review step froze code/address-pr-comments correctly, so the miss is not the frozen-snapshot bug (#698); it is that nothing surfaces an unanswered thread to the owner, who merges from the GitHub UI where unresolved threads do not block, and the on-demand assist was invoked once in four weeks. Decision: keep the owner gate (merge and thread resolution stay human) and add post-merge detection, not prevention. When the autoclose sweep closes a ticket on a merged PR, fetch the PR's reviewThreads once and, for each thread that is unresolved, not outdated, and has only its opening comment, name it in the sweep summary and Slack line the same way autoclose already names the retire follow-up - report only, never resolve or reply. Rationale: the sweep is the one place that already touches every merged PR, the signal lands in coga/log.md where it is legible, and no new poller or hidden state is added. Out of scope: resolving threads, blocking merges, or running an agent on the review step automatically.

## Context

<!-- coga:blackboard -->

## Dev

branch: autoclose-unanswered-threads
worktree: /home/n/Code/claude/coga-autoclose-unanswered-threads

## Plan (implement, 2026-09-15)

- Fetch point: `autoclose._try_bump_one`, after `pr_state` says MERGED and
  before `mark_done`. One paginated `gh api graphql` `reviewThreads` query per
  closed PR (`comments(first: 1) { totalCount ... }` — "only its opening
  comment" is `totalCount == 1`, so no per-thread comment pagination).
- Filter: `not isResolved and not isOutdated and totalCount == 1`.
- Carry: `ClosedTicket.unanswered_threads` (tuple of `ReviewThread`:
  path, line, author, url, first body line).
- Surfaces, mirroring the retire follow-up: the closure's `log.md` line names
  the threads (that is the durable one); a
  `## Autoclose Sweep: unanswered review threads` section on the period task
  blackboard / stdout; one trailing 💬 Slack line. The per-ticket 🎉 line is
  left alone, same reasoning as retire.
- Failure: a `GhError` from the thread fetch propagates like `pr_state`'s and
  runs *before* the close, so the ticket stays open and retries next sweep
  rather than closing without its report. Never resolves or replies.
- Doc twins: `coga/skills/coga/autoclose/sweep`, `recurring/autoclose-merged`
  ticket, `dev/code` context "Review threads that merge unanswered" (live +
  packaged).

## Implement handoff (2026-09-15)

Commit `6fe6ff0d` on `autoclose-unanswered-threads`, rebased on current
`origin/main` (no incoming commits). Full suite: 2511 passed.

What changed (`src/coga/autoclose.py`):
- `ReviewThread` (path, line, author, url, excerpt) and
  `ClosedTicket.pr_url` / `.unanswered_threads`; `AutocloseResult.review_threads_pending`.
- `pr_review_threads(url)`: paginated `gh api graphql` on the base repo's
  `reviewThreads`, `comments(first: 1) { totalCount }`. Verified read-only
  against real PRs: 699 → 1 thread, 705 → 1 thread, 800 → 0 — matches the
  ticket's finding.
- `unanswered_review_threads(url)`: keeps `not isResolved and not isOutdated
  and totalCount == 1`; `line` falls back to `originalLine`; excerpt strips
  the Codex badge markup (`**<sub>![P1 Badge](…)</sub> Title**` →
  `P1 Badge Title`), clipped to 80 chars.
- `_try_bump_one` fetches before `mark_done` and appends `; N unanswered
  review thread(s): path:line, …` to the `log.md` closure line.
- `_report_followup` is the shared delivery (blackboard-or-stdout + one
  Slack `post`) now used by both the retire and the 🧵 thread follow-ups;
  recipe calls `_report_followups` on every exit path it used before.

Decisions:
- Fetch failure propagates as `GhError` *before* the close → ticket stays
  open, next sweep retries. Chosen over "close and skip the report" because
  silent closure is the exact miss this ticket fixes, and over swallowing
  because the recurring sweep runs loud by design.
- Slack emoji is 🧵, not 💬: `coga slack` FYIs already use 💬 and the
  notification tests filter posts by emoji.
- Per-ticket 🎉 line untouched, same reasoning the retire follow-up recorded.

Tests: 13 new in `tests/test_autoclose.py` (filter, pagination/coordinates,
fallbacks, excerpt, GhError paths, sweep records + audit line, fetch failure
leaves ticket open, report/summary renderers, recipe stdout+Slack, both
follow-ups together, blackboard append). `_stub_pr_state` now also stubs the
thread fetch to `[]`; the two direct `pr_state` stubs in
`test_notification_messages.py` got the same.

Docs (live + packaged twins): `coga/skills/coga/autoclose/sweep/SKILL.md`
gains "The unanswered-thread follow-up"; `recurring/autoclose-merged/ticket.md`
step 7 + blackboard note; `contexts/dev/code` decision paragraph now
describes landed behavior and points at the skill instead of this ticket.

Not done / out of scope: resolving threads, blocking merges, auto-launching
the assist. No adjacent bugs found.
