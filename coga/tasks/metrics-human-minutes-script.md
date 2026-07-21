---
slug: metrics-human-minutes-script
title: Metrics human minutes script
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- marketing/plan
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 4 (review)
---

## Description

Build `scripts/human_minutes.py`: compute human attention per task and per day
from public, timestamped records, so anyone can recompute the numbers behind
the "20 minutes a day" launch post (`marketing/launch-20-minutes-a-day`).

Behavior:

- **Event sources (merged):** (1) `coga/log.md` lines with `[human:*]` actors;
  (2) git commits by human authors, *excluding* coga auto-commits (message
  prefixes "Sync coga state", "Log:", "Ticket:"); (3) GitHub-side PR events
  via `gh` — reviews, merges, comments (server-held timestamps, preferred
  because they cannot be locally backdated).
- **Episode clustering:** sort events per task (and per day); a gap > 10 min
  starts a new episode; episode duration = last − first, with a 2-minute floor
  for isolated events. Both parameters are flags; output always includes a
  sensitivity line at floor = 5 min.
- **Outputs:** (a) per-task table: task → minutes → episodes → artifact link
  if the ticket names one; (b) per-day derived diary: date → minutes →
  blockers answered (linked) → tasks advanced; (c) machine-readable JSON.
- **Attribution:** a task's events are matched by task ref in log lines, and
  by branch/PR association for git/gh events (via the ticket's recorded PR).
- **Test fixture:** the July 1–2 megalaunch burst (9 tasks, actor
  `[megalaunch]` in log.md). Expected order of magnitude from log-only events:
  2–12 min/task — gh integration should raise these somewhat.

Added 2026-07-15 (launch prep): the run also needs **machine-side token
accounting** — tokens consumed during the window (autonomous vs interactive
where distinguishable, e.g. from Claude Code / codex usage stats), so the
launch post can report tokens → API-equivalent price → actual flat
subscription cost. May be a separate small script; decide at implement time
whether it lives here or as its own ticket — but the capture method must
exist before the run starts.

Optional follow-up (may be its own ticket): a CI job that runs the script on
the public repo and publishes the table, so the number is produced on neutral
infrastructure ("the repo computes its own ledger").

Design intent: measurement from records, not self-report. No new product
instrumentation — everything derives from what coga/git/gh already record.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/602
branch: human-minutes-ledger
worktree: /tmp/coga-human-minutes-peer-review.OeLDzU/repo

## Implementation notes

- Build the recomputation surface as a plain `scripts/human_minutes.py` CLI with
  deterministic parsers and fixture-backed tests. Git and GitHub remain explicit
  external record sources; missing `gh` data must fail loud unless the operator
  deliberately selects log-only/offline input.
- Token capture already exists in schema-2 `[system]` usage records in
  `coga/log.md` (`src/coga/usage.py`). This script will account for those records
  in the requested window and classify sessions by recorded human turns where
  distinguishable, instead of adding new product instrumentation or a second
  capture path.
- CI publication remains out of scope as the ticket labels it optional.

## Progress

- Added `scripts/human_minutes.py`: markdown and JSON ledgers, per-task and
  per-day episode clustering, log-line blocker permalinks, task advancement,
  recorded-PR artifact links, PR-associated human git commits with Coga
  auto-commit exclusion, and human GitHub reviews/comments/merges (including
  inline review comments).
- The gap and isolated-event floor are flags. A gap exactly equal to the
  threshold stays in the same episode; only a strictly greater gap splits it.
  The output always recomputes the 5-minute isolated-event sensitivity case.
- Schema-2 usage records are rolled up by mode and model. Transcript-derived
  `human_turns == 0` is autonomous, `> 0` interactive, and absent data remains
  visibly unknown. Pricing is deliberately not hard-coded; the pre-registered
  run price can be applied to the JSON per-model buckets.
- Added a deterministic July 1–2 fixture with nine megalaunch-attempted tasks;
  its log-only task totals are all 2–12 minutes. Fixture-backed GitHub JSON
  proves review/comment/merge collection without network or clock dependence.
- Verification so far: focused tests `5 passed`; full suite `1327 passed, 1
  skipped`. A real July 1–2 offline run also rendered successfully. Direct
  `gh pr view` and the inline-comment API shape were smoke-tested, while this
  managed sandbox withholds keyring auth from Python child processes; the
  default script correctly failed loud rather than emitting a partial ledger.

## Implement handoff

- Commit: `69f8453bfacbb59c13ff648415e4b543ab6ba702` (`Add recomputable
  human-minutes ledger`; ticket named in commit body).
- Files: executable `scripts/human_minutes.py`, matching tests and July burst
  fixture, plus the durable measurement/token-accounting contract in
  `coga/contexts/marketing/plan/SKILL.md`.
- Verification after the final rebase: `PYTHONPATH=$PWD/src python3.12 -m
  pytest` → `1327 passed, 1 skipped`; executable real-log JSON/markdown smoke
  checks passed; cached diff check passed.
- Freshness/publication: rebased onto live `origin/main` at `54d4a57c`; branch
  is clean, `0` behind / `1` ahead, not pushed, and has no PR. The one skipped
  test is the suite's existing Hatchling-dependent packaging gate; this change
  does not alter packaging.

## Peer review

- Native `codex review --base main` found six correctness issues worth fixing:
  inherited human git identities could misattribute agent commits, merged log
  histories could double-count records, loose progress and PR matching could
  admit unrelated prose or URLs, an unresolved git base silently widened the
  commit scan, and blocker answers were truncated in the audit ledger.
- Fixed attribution by excluding commits inside recorded Coga agent-session
  windows and failing loud when author-matched commits predate schema-2 session
  coverage. Exact duplicate union-merge log lines are now collapsed, while
  genuinely distinct events at the same timestamp remain countable.
- Anchored task progress and recorded-PR parsing to canonical log transitions,
  made unresolved git bases fatal, and render blocker answers verbatim.
- The linked worktree's git metadata was read-only in this managed sandbox, so
  the reviewed branch was committed in the documented independent-clone
  fallback at `/tmp/coga-human-minutes-peer-review.OeLDzU/repo`.
- Final commits: `761d6041` (`Add recomputable human-minutes ledger`) and
  `65f23bdf` (`peer-review: fix human-minutes attribution`). The branch is
  rebased onto live `origin/main` at `92a4c94f`, clean, and `0` behind / `2`
  ahead.
- Verification: focused tests `7 passed`; full suite `1329 passed, 1 skipped`;
  July 1–2 offline JSON and Markdown smoke checks passed, including unabridged
  blocker-answer rendering. The skip is the existing Hatchling-dependent
  packaging gate and is unrelated to this change.

## PR

### Summary

- Add a recomputable human-attention ledger built from Coga human log events,
  PR-associated git commits, and server-held GitHub review, comment, and merge
  timestamps, with per-task/per-day Markdown, stable JSON, and the required
  five-minute sensitivity result.
- Account for schema-2 machine token usage by autonomous, interactive, and
  unknown mode with per-model buckets, without adding a second capture path or
  hard-coding prices.
- Harden claim integrity with agent-session commit exclusion, fail-loud git
  coverage and base checks, union-log deduplication, canonical task/PR parsing,
  verbatim blocker answers, deterministic fixtures, and a durable measurement
  contract update.

### Test plan

`PYTHONPATH="$PWD/src" python3.12 -m pytest` (`1329 passed, 1 skipped`); July 1–2 offline JSON and Markdown smoke checks passed.
