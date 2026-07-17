---
slug: log-md-coga-chat-too-so-we-have-a-full-view-of-the
title: log.md coga chat too so we have a full view of the work
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/usage
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

Extend Coga's repo-global `coga/log.md` session records to cover every
Coga-launched agent interaction, including stateless discussion entry points
such as `coga chat` and `coga ticket`. Each completed session should leave one
structured, human-legible record showing wall-clock time, the human's
participation and request, and the agent's outcome, so the log provides a full
chronology of time spent and work performed rather than token usage alone.

Keep this local, append-only, git-backed, and session-level. Do not turn
`log.md` into a raw turn-by-turn transcript or infer an inaccurate "active
typing time."

## Context

- The current capture path is `src/coga/commands/launch.py::spawn_agent_session`
  plus `src/coga/usage.py`. It already records a UTC start/end window for
  parsing, but `UsageRecord` persists only the end timestamp and token fields.
- Current capture deliberately excludes stateless bootstrap launches. Remove
  that blind spot so task launches, `coga chat`, `coga ticket`, onboarding, and
  other Coga-launched agent sessions use the same post-session record path.
  Script steps and lifecycle commands have no agent transcript and should keep
  their existing audit-log events rather than receiving invented session data.
- Emit one structured record per agent session. It must include an explicit
  start/end or start/duration representation, wall-clock elapsed time, human
  and agent turn counts, enough bounded request content to show what the human
  contributed, and enough bounded final-outcome content to show what the agent
  did. Preserve the existing token/provider/model/session metadata and the
  `coga usage` read surface.
- Count only explicit human/user and agent/assistant text authored inside the
  capture window. Exclude system/developer prompts, injected kickoff tokens,
  tool calls, and tool results. Combine the explicit human-authored text in
  chronological order for the request field; use the last available explicit
  assistant text for the outcome field.
- Normalize request and outcome text to one line and cap each at 500 Unicode
  characters, using a visible truncation marker. Replace exact configured
  secret values with `[REDACTED]` before writing; if content extraction or
  redaction cannot complete safely, still record timing, counts, metadata, and
  status but leave the content fields null.
- "Human time" is represented by the human-authored turns and whole-session
  wall clock. Transcript gaps are not reliable typing measurements, so do not
  label them as active human time.
- Tag stateless sessions with their bootstrap identity (for example,
  `bootstrap/orient` for `coga chat`), their bootstrap title, and a null step.
  Failed, timed-out, and interrupted sessions must still emit a record with an
  explicit outcome status and the last safely available outcome text, if any.
- Evolve the record schema compatibly: existing schema-v1 usage records must
  remain readable with the new activity fields absent/null and must not be
  rejected or misrepresented in rollups.
- The record must remain a single bounded JSON message inside the standard
  `coga/log.md` line shape; do not append the full raw transcript. Treat
  transcript text as potentially sensitive and avoid accidental secret
  exposure in committed history.
- Update the `coga/usage` behavioral context with the shipped contract, and
  check the live and packaged Coga OS copies for any matching template that
  must stay synchronized. Add focused launch/usage tests for both ordinary task
  sessions and stateless discussion sessions, plus compatibility coverage for
  older usage records already present in `log.md`.
<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decisions

- Approved schema 2 extends the existing usage record without replacing its
  token fields. `ts` remains the session-end timestamp used by current filters;
  new activity fields are `started_at`, `ended_at`, `elapsed_seconds`,
  `human_turns`, `agent_turns`, `request`, `outcome`, `content_status`, and
  `outcome_status`.
- `request` combines explicit human-authored turns in chronological order;
  `outcome` is the last explicit assistant-authored text. Both are normalized
  to one line, redacted, and capped at 500 Unicode characters.
- `content_status` is `ok` or `unknown`. Unsafe extraction or redaction leaves
  both content fields null while preserving timing, counts, metadata, and
  session status. `outcome_status` is `completed`, `failed`, `timed_out`,
  `interrupted`, or `unknown`; it remains independent of token `usage_status`.
- Schema-1 log records remain readable with schema-2-only fields absent/null.
- Capture belongs in the shared real-agent spawn path so task, chat, ticket,
  project/onboarding, and megalaunch sessions cannot opt out accidentally.
  Script paths and process spawn failures still emit no session record.

## Dev

pr: https://github.com/FastJVM/coga/pull/583
branch: log-session-activity
worktree: /tmp/coga-log-session-activity
commits:
- e2c4f634 Record activity for every agent session
- 64034b68 peer-review: apply review findings

## Implementation

- `src/coga/usage.py` now writes schema-2 session records with start/end,
  elapsed wall time, human/agent text-turn counts, bounded request/outcome,
  independent content and process-outcome statuses, and the existing token
  metadata. The loader accepts schema 1 and leaves new fields null.
- Claude and Codex parsers extract only timestamp-windowed explicit text.
  Launcher prompt/kickoff text, Codex startup context, system/developer content,
  tool calls, and tool results are excluded. Exact configured secret values are
  redacted before one-line normalization and 500-character truncation.
- The shared real-agent spawn path always captures after a process starts.
  Bootstrap sessions are recorded with bootstrap identity/title and null step;
  guided authoring against a real task explicitly records as
  `bootstrap/ticket`. Script paths and spawn failures remain uncaptured.
- Failed, timed-out, and interrupted sessions map to explicit outcome statuses
  while still parsing the last safely available assistant text.
- Updated the live `coga/usage` behavioral context. No matching packaged usage
  context exists under `src/coga/resources/templates/coga/`, so there was no
  second copy to synchronize.

## Verification

- Focused launch/usage/ticket/project/megalaunch set: 148 passed.
- Full suite with the worktree's absolute source path:
  `PYTHONPATH=/tmp/coga-log-session-activity/src python -m pytest` — 1246
  passed, 1 skipped.
- Plain `python -m pytest` exposed the known relative-`PYTHONPATH` bootstrap
  subprocess failure in
  `tests/test_launch_script.py::test_bootstrap_script_launch_is_stateless`;
  the same failure reproduced on unchanged `main`. The absolute source path
  makes the subprocess import deterministic and the full suite passes.
- `PYTHONPATH=/tmp/coga-log-session-activity/src python -m coga.cli validate
  --task log-md-coga-chat-too-so-we-have-a-full-view-of-the --json` from the
  primary checkout: 1 ok, no issues.
- `git diff --check`: clean.
- Freshness: fetched `origin/main` at `f7cc12c6`, rebased cleanly, then reran
  the full suite (1246 passed, 1 skipped). Feature worktree is clean; branch is
  0 behind / 2 ahead of that `origin/main` snapshot.

## Peer review

- Native `codex review --base main` found two must-fix issues: guided ticket
  authoring could leave the session record uncommitted on failed/no-change
  exits, and ambient authoring environments could redact the wrong value for
  a declared secret.
- The shared teardown now always syncs the session log independently of the
  authoring finalizer, including failed sessions. Secret redaction now
  distinguishes scoped launch environments from ambient authoring
  environments, uses the declared `env:` source value, and suppresses content
  when an `op://` value cannot be proven safe.
- Added regression coverage for failed authoring-session durability and both
  ambient/scoped secret-value selection paths.
- Rebased cleanly onto current `origin/main` at `ad2ed0ae`. Final branch state:
  clean, 0 behind / 2 ahead. Post-rebase full suite:
  `PYTHONPATH=/tmp/coga-log-session-activity/src python -m pytest` — 1250
  passed, 1 skipped. `git diff --check` is clean.

## PR

### Summary

- Record bounded schema-2 activity alongside token usage for every
  Coga-launched agent session, including chat, ticket authoring, project
  planning, task work, and megalaunch.
- Capture wall-clock timing, explicit human/agent turn counts, redacted request
  and final-outcome summaries, and process outcome status while keeping
  schema-1 records readable through `coga usage`.
- Keep failed and stateless sessions durable through the shared log-sync path,
  with conservative secret handling that leaves content null whenever safe
  redaction cannot be established.

### Test plan

`PYTHONPATH=/tmp/coga-log-session-activity/src python -m pytest` — 1250 passed, 1 skipped.
