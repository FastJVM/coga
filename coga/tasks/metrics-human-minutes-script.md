---
slug: metrics-human-minutes-script
title: Metrics human minutes script
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
