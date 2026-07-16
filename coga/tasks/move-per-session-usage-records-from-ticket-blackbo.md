---
slug: move-per-session-usage-records-from-ticket-blackbo
title: Move per-session usage records from ticket blackboards to log.md
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Move the per-session usage records `coga launch` captures out of each
ticket's `## Usage` blackboard section and into the repo-global
`coga/log.md`, as ordinary tagged JSON lines.

Why: the blackboard is composed into every launch prompt, so usage records —
pure accounting history no agent needs for the next step — bloat every future
prompt on that ticket. `log.md` is the durable-history home: append-only,
never composed, tagged per task, and it outlives the task (`coga delete` /
retire removes the task directory and today takes its usage history with it).
It also removes the extra `sync_coga_state` commit in
`src/coga/commands/launch.py` that exists only because the record lands in
the ticket *after* the agent's final bump/mark sync — `log.md` already has
its own conflict-free merge=union sync path (`sync_log`).

Decided (2026-07-16, owner): write the existing `UsageRecord` JSON line
directly into `log.md` as the entry's payload — JSON is human-readable
enough; no sibling `usage.jsonl` file. Keep the standard log-line tagging
(task ref + timestamp) so `coga usage --task` filtering still works.

Scope:

- `capture_session` / `append_record` in `src/coga/usage.py`: append the
  record to `log.md` (via the shared `append_log` path so formatting and
  tagging stay uniform) instead of the ticket's `## Usage` section.
- `coga usage` rollup (`load_records` / `_usage_blackboards`): parse records
  from `log.md` instead of globbing every ticket `.md`.
- Drop the post-capture `sync_coga_state` call in `commands/launch.py`;
  reuse the log sync instead.
- Migration: per stage posture, no back-compat parsing of old `## Usage`
  sections required — but decide whether the rollup should still read them
  during the transition or existing records are simply forgotten.
- Update the `coga/cli` context (`coga usage` description) and the
  architecture context if it names the `## Usage` blackboard section;
  packaged copies under `src/coga/resources/templates/` and any live
  `coga/contexts/` override in the same PR.
- Tests: `tests/test_usage*.py` and any launch tests asserting the
  blackboard write.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
