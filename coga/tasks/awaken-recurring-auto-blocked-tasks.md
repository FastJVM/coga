---
slug: awaken-recurring-auto-blocked-tasks
title: Awaken recurring auto blocked tasks
status: in_progress
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
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

Follow up to `async-park-and-continue-on-block`.

That task lets a recurring sweep park a blocked task cleanly and continue the
rest of the run. This task should add the missing wakeup loop for parked asks:
recurring/auto tasks that panic with an unresolved blocker should be surfaced
again later so they do not disappear into `in_progress` state after the first
Slack post.

Build a markdown-first wake mechanism, not a hosted service:

- Detect recurring task instances that are still `in_progress` and have open
  blocker asks in their blackboard.
- Re-notify the owner with the task slug, blocker text, and the next command
  to resume (`coga launch <slug>` or `coga recurring`), using the existing
  notification/sync surfaces.
- Deduplicate reminders so the same blocker is not posted on every scan. Store
  any reminder watermark in Coga markdown state, preferably the recurring
  template blackboard or a small recurring-inbox task blackboard.
- Preserve the async-park contract: do not hold a live REPL open, do not launch
  nested sessions, and do not treat panic as work to keep trying immediately.
- Define the human answer handshake. The simplest acceptable contract is that
  the human edits the parked task blackboard with an answer or resolved marker;
  the next `coga launch` / sweep resumes from the task files.
- Cover the behavior with tests that prove a parked recurring task is surfaced
  again, duplicate reminders are suppressed, and answered/resolved blockers are
  not re-awakened.

Open design question to settle before implementation:

Should the wake/drain path eventually attempt all `active` tasks, or only
recurring/auto-ready work? Removing `autonomy:` entirely would make `status:
active` mean both "approved" and "safe to run unattended", which may be too
coarse. If the decision is to collapse that model, update the Coga
architecture/CLI contexts in the same PR and migrate the task-selection rules
explicitly rather than doing it as a side effect of blocker reminders.

## Context

Relevant existing pieces:

- `async-park-and-continue-on-block` defines the park-and-resume behavior.
- `v2/issue-inbox-slack` covers richer immediate Slack posts for blockers.
- `nightly-auto-drain-run-for-ready-tickets` is the future drain loop that may
  consume this wakeup behavior.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":852736,"cli":"codex","input_tokens":229218,"model":"gpt-5.5","output_tokens":7989,"provider":"openai","schema":1,"session_id":"019f1a9b-efdc-7d02-84bb-575d0705e997","slug":"awaken-recurring-auto-blocked-tasks","step":"implement","title":"Awaken recurring auto blocked tasks","ts":"2026-06-30T22:42:53.272515Z","usage_status":"ok"}
