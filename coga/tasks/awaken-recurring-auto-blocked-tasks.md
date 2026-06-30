---
slug: awaken-recurring-auto-blocked-tasks
title: Awaken recurring auto blocked tasks
status: in_progress
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/architecture
- coga/cli
- coga/sync
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
step: 3 (open-pr)
---

## Description

Follow up to `async-park-and-continue-on-block`.

That task lets a sweep park a blocked task cleanly and continue the rest of the
run. This task should add the missing visibility and wakeup loop for parked
asks: any task with an unresolved blocker should remain visible in the normal
operator surfaces and be surfaced again later, so it does not disappear into
`in_progress` state after the first Slack post.

Build a markdown-first blocker queue, not a hosted service:

- Add a shared scanner for unresolved blockers in task blackboards. It should
  walk regular tasks with the existing task-listing primitives; do not special
  case recurring identity as the data model. Recurring-created tasks are still
  just tasks.
- Make `coga status` show blockers without opening each ticket. Keep the
  current task table, then append a second `Open blockers` table when any
  unresolved blockers exist. The table should show task slug, status, step,
  owner, blocker text, age if available, and the next command.
- Define the human answer handshake in markdown. The simplest acceptable
  contract is that a human edits the task blackboard with an `answered:` or
  `resolved:` marker after the blocker; the next `coga launch <slug>` resumes
  from task files.
- Re-notify owners for unresolved parked blockers from an unattended scan path,
  using the same scanner as `coga status` and the existing notification/sync
  surfaces. A recurring sweep can call this opportunistically, but recurring is
  the trigger path, not the blocker model.
- Deduplicate reminder posts so the same unresolved blocker is not posted on
  every scan. Store the reminder watermark in markdown state on the blocked
  task's own blackboard so it travels with the ask and remains inspectable.
- Preserve the async-park contract: do not hold a live REPL open, do not launch
  nested sessions, and do not treat panic as work to keep trying immediately.
- Cover the behavior with tests that prove blockers appear in `coga status`,
  reminders are posted once, duplicate reminders are suppressed, and
  answered/resolved blockers disappear from the queue and are not re-awakened.

Product decision for this ticket:

This ticket does not change task selection, `autonomy:`, or the broader drain
model. It only makes unresolved blocker asks visible and reminds owners. Future
work may decide whether a drain path should attempt all active agent-owned work,
but that migration must be explicit and should not happen as a side effect of
blocker reminders.

## Context

Relevant existing pieces:

- `async-park-and-continue-on-block` defines the park-and-resume behavior.
- `v2/issue-inbox-slack` covers richer immediate Slack posts for blockers.
- `nightly-auto-drain-run-for-ready-tickets` is the future drain loop that may
  consume this wakeup behavior.

Implementation shape:

- Factor blocker parsing into reusable code instead of duplicating regexes in
  status and recurring.
- Treat a blocker entry as open until a later answer/resolution marker closes
  it. Support at least `answered:` and `resolved:` in a form that is easy for a
  human to type in markdown.
- The canonical next command is `coga launch <slug>`. If a reminder is emitted
  during a recurring sweep, the message may also mention `coga recurring`, but
  the task slug remains the resume target.
- If reminder watermarking needs a section name, prefer a small plain-markdown
  section in the blocked task blackboard such as `## Blocker reminders`; keep it
  compact and machine-readable enough to deduplicate by blocker fingerprint.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design decision

- [2026-06-30] Revised scope with Nick: blocker visibility is generic task
  behavior, not recurring identity behavior. `coga status` should append an
  `Open blockers` table after the normal task table. Reminder posting reuses
  that scanner and can be triggered by recurring sweeps, but blocker state and
  dedup watermarks live on the blocked task's own blackboard.
- [2026-06-30] Follow-up clarification: `coga status` should directly scan the
  task blackboards it is already reading and append the blocker table. Reminder
  posts/watermark writes stay out of `status` and belong in an explicit
  script-backed recurring task.

## Dev

branch: codex/awaken-blocker-reminders
worktree: /tmp/coga-awaken-blocker-reminders

Implementation notes:

- Added `coga.blockers` as the shared markdown scanner/watermark writer for
  open blocker asks. It reads `## Blockers`, closes entries on later
  `answered:` / `resolved:` lines, and records reminder watermarks under
  `## Blocker reminders`.
- Wired `coga status` to append an `Open blockers` table from that scanner
  while staying read-only.
- Added the script-backed `recurring/blocker-reminders` battery with matching
  workflow and `coga/blockers/remind` skill in both live and packaged template
  trees.
- Updated sync/CLI contexts for the new status visibility and live reminder
  notification path.

Verification:

- `PYTHONPATH=/tmp/coga-awaken-blocker-reminders/src python -m pytest`
- `git diff --check`
- `PYTHONPATH=/tmp/coga-awaken-blocker-reminders/src python -m coga.cli validate --task awaken-recurring-auto-blocked-tasks --json`

Peer review:

- [2026-06-30] Ran `codex review --base main` from
  `/tmp/coga-awaken-blocker-reminders` (sandboxed run hit Codex app-server
  read-only FS; escalated rerun completed). Review found one P2 bug:
  indented Markdown sub-bullets under a blocker were parsed as separate open
  blockers. Fixed on the feature branch in commit `9571c187`
  (`peer-review: fix nested blocker bullets`) by restricting blocker starts to
  top-level bullets and adding a regression test.
- Verification after peer-review fix:
  `PYTHONPATH=src python -m pytest tests/test_blockers.py tests/test_commands.py::test_status_appends_open_blockers_table -q`
  (6 passed), `PYTHONPATH=src python -m pytest` (941 passed, 1 skipped),
  `git diff --check`, and
  `PYTHONPATH=src python -m coga.cli validate --task awaken-recurring-auto-blocked-tasks --json`
  (ok_count 1, no issues).

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":852736,"cli":"codex","input_tokens":229218,"model":"gpt-5.5","output_tokens":7989,"provider":"openai","schema":1,"session_id":"019f1a9b-efdc-7d02-84bb-575d0705e997","slug":"awaken-recurring-auto-blocked-tasks","step":"implement","title":"Awaken recurring auto blocked tasks","ts":"2026-06-30T22:42:53.272515Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":8725888,"cli":"codex","input_tokens":373990,"model":"gpt-5.5","output_tokens":32935,"provider":"openai","schema":1,"session_id":"019f1ab6-2928-70c0-8dc8-24549642ea34","slug":"awaken-recurring-auto-blocked-tasks","step":"implement","title":"Awaken recurring auto blocked tasks","ts":"2026-06-30T23:15:36.431722Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":2627072,"cli":"codex","input_tokens":125351,"model":"gpt-5.5","output_tokens":5973,"provider":"openai","schema":1,"session_id":"019f1ad1-1abf-7921-93c4-5fcf616eb792","slug":"awaken-recurring-auto-blocked-tasks","step":"peer-review","title":"Awaken recurring auto blocked tasks","ts":"2026-06-30T23:44:30.059633Z","usage_status":"ok"}
