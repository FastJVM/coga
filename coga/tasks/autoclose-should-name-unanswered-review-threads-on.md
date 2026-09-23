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

## Peer review

2026-09-15: `codex review --base main` **returned** (exit 0;
transcript `/tmp/coga-autoclose-peer-review.log`). All three must-fix findings
were reproduced and fixed in `1c414750`:

- P1: finish the paginated thread lookup before the final ticket re-read,
  preserving a concurrent pause, cancellation, or completion and avoiding
  duplicate completion events.
- P2: use the recorded PR hostname on every GraphQL page, including GitHub
  Enterprise and when `GH_HOST` names a different host.
- P2: send owner/repository with raw `-f` fields, preserving names such as
  `123`, `true`, and `null` as strings.

Also corrected stale retire-only report descriptions in `coga/recurring` and
`coga/sync`, and the historical baseline in `dev/code`; all affected live and
packaged twins match. No design rethink or unresolved code finding.

Verification:

- New regression cases: `PYTHONPATH=/home/n/Code/claude/coga-autoclose-unanswered-threads/src /home/n/Code/claude/coga/.venv/bin/python -m pytest tests/test_autoclose.py -k 'paginates_and_passes_base_repo_coordinates or preserves_a_transition_during_review_thread_lookup' -q -p no:cacheprovider`
  → 7 failed before fixes; 7 passed, 77 deselected afterwards.
- Full suite after fixes and rebase: `PYTHONPATH=/home/n/Code/claude/coga-autoclose-unanswered-threads/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  → **2517 passed in 225.84s**. Transcript:
  `/tmp/coga-autoclose-peer-tests-final.log`. Use this venv: ambient `python`
  lacks `tomlkit`.
- `git diff --check` → clean.
- `coga validate --task autoclose-should-name-unanswered-review-threads-on --json`
  from the primary checkout → 1 valid task, no issues.
- `git fetch origin main && git rebase FETCH_HEAD` completed without conflicts.
  Implementation commit is now `cef8037a`; fixes are `1c414750`. Feature branch
  contains current fetched `origin/main` (`5894147a`), with both commits ahead.

Live read-only query confirmed PR 699 → 1, PR 705 → 1, PR 800 → 0 unanswered
threads. Drove the production report delivery with those results in actual
80×24 and 120×40 PTYs, Slack disabled: audit locations, report authors,
badge-stripped excerpts, and full thread URLs were present; the clean PR
produced no report. Probe: `/tmp/coga-autoclose-output-probe.py`.
This verifies terminal output and the suppressed Slack payload, **not** the
rendered Slack message. Available tools include no browser-control runtime
or Slack visual client; the Browser skill was inspected and its required
execution tool is not available. The current peer-review instructions require
driving a changed human-visible surface and say that record is the gate.
**Blocked on that remaining check; do not advance to open-pr yet.**

To resume: inspect the new 🧵 summary in a rendered Slack preview/client at
normal and narrow widths, confirm that PR labels and every path:line link
remain readable and open the intended thread, and record the result here.
Provide an accessible browser/Slack visual session for the agent, or record
the human's visual verification. The code fixes, tests, and PR body below
are complete; rebase/test again only if the branch has materially drifted.

## PR

Autoclose now reports unresolved, non-outdated review threads that contain
only their opening comment when it closes a ticket on a merged PR. The
closure audit line names their locations, the sweep report includes authors,
opening-line excerpts, and thread URLs, and one Slack follow-up links every
thread.

The read-only lookup paginates against the recorded PR's host and base
repository. A fetch failure leaves the ticket open for retry, and eligibility
is rechecked after the network calls to preserve concurrent human transitions.
Updated the autoclose contract, recurring and notification contexts, and
their packaged twins.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-autoclose-unanswered-threads/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` — 2517 passed; regressions reproduced before fixes; read-only PR 699/705/800 probe and report inspection in 80×24 and 120×40 PTYs.

---

## Blockers

- [ ] [2026-09-15 16:54] [agent:codex] id=20260915T165417 Peer-review requires a rendered Slack check for the new thread summary. Provide an accessible browser/Slack visual session, or record human verification at normal and narrow widths that PR labels and every path:line link render correctly and open the intended thread. This session has no visual client. Codex review returned; all three findings are fixed in 1c414750, the rebased branch is clean, 2517 tests passed, and the PR body and terminal QA are on the blackboard.

---

## Blocker reminders

- e56cebde79e4 last_reminded: 2026-09-16 10:58
