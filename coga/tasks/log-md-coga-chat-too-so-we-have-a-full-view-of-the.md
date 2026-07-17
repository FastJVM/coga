---
slug: log-md-coga-chat-too-so-we-have-a-full-view-of-the
title: log.md coga chat too so we have a full view of the work
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/usage
skills: []
workflow: code/with-review
secrets: null
script: null
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
- "Human time" is represented by the human-authored turns and whole-session
  wall clock. Transcript gaps are not reliable typing measurements, so do not
  label them as active human time.
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

## Ticket authoring notes

- Intent: make `coga/log.md` show every Coga-managed interaction, including `coga chat`, so elapsed time and completed work are visible in one durable chronology.
- Current behavior: task launches append one per-session token-usage JSON record, but stateless bootstrap launches such as `coga chat` and `coga ticket` are deliberately excluded. Launch already records a start/end window internally, but the persisted usage schema has no elapsed-duration field.
- Decisions: one bounded structured record per session, exact wall clock including idle time, all Coga-launched agent sessions, and human contribution represented by authored turns rather than a guessed typing-time metric.
- Workflow: `code/with-review`; Claude implements, Codex peer-reviews, and the owner reviews the PR.

## Evaluator review

The ticket is clear enough to start: it identifies the current capture seam, the desired per-session record, exclusions, compatibility requirement, documentation touchpoint, and focused test surfaces. `code/with-review` fits a cross-cutting launch/usage schema change that handles potentially sensitive transcript content and merits independent review plus an owner gate.

The attached `coga/usage` context is directly relevant and appropriately scoped. No additional broad context is necessary; the ticket already supplies the needed launch and sync facts, and the implementer can inspect the named source paths. The scope is cohesive as one ticket: schema evolution, capture for stateless sessions, reader compatibility, documentation, and tests are all required to ship the same behavior safely.

Before implementation, the ticket should resolve or explicitly delegate these design choices:

- Define the exact bounding and secret-safety policy for request/outcome text: character or byte limits, truncation marker, multiline normalization, and whether any redaction is required beyond truncation.
- Define which transcript entries count as human and agent turns, especially injected kickoff prompts, tool/result messages, resumed sessions, and sessions ending without a normal final assistant response.
- Define how stateless records are tagged in the standard log shape and what `slug`, `title`, and `step` contain when there is no real task.
- State the schema-version/reader behavior for older records missing the new timing, turn-count, and summary fields.
- Clarify whether failed, timed-out, or interrupted agent sessions still emit bounded request/outcome fields and how their outcome is represented.

These are bounded implementation decisions rather than evidence that the ticket needs splitting, but ambiguity around redaction and stateless identity could otherwise produce materially different contracts.
