---
slug: log-md-coga-chat-too-so-we-have-a-full-view-of-the
title: log.md coga chat too so we have a full view of the work
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
