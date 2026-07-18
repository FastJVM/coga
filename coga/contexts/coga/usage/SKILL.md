---
name: coga/usage
description: How coga records agent-session activity and token usage — bounded schema-2 JSON records appended as tagged lines to the repo-global `coga/log.md`, the Claude/Codex parser seam, and `coga usage` as the token-rollup surface. Local and committed, never a phone-home. Read before touching session capture or adding a usage consumer.
---

# Agent Session Activity and Usage

Coga records the activity and token usage of every Coga-launched agent session
as plain committed text and reads token rollups back with `coga usage`. This is
a foundational **local** data primitive
— JSONL lines in the repo, nothing sent off-machine — and is **not** the
phone-home telemetry `coga/principles` #5 forbids (that ban is about
external/anonymized install or usage pings; this records only into the repo's own
git-tracked files). Its consumers (agent autorouting, digest/report views) are
separate tickets; this primitive ships the records and the reader, and
deliberately defines no budget cap or "remaining".

## The store — the repo-global `coga/log.md`, tagged per task

There is **no `coga/usage/` directory, no dedicated ledger file, and no
per-task store.** Each agent session appends exactly one self-describing JSON
record to the repo-global `coga/log.md`, riding the standard log-line shape
(`YYYY-MM-DD HH:MM [<task-ref>] [system] <record JSON>`) via the shared
`append_log` path, so tagging and formatting stay uniform with every other
log line. The log is the durable-history home: append-only, **never** a
prompt-composition layer, and it outlives the task (`coga delete` / retire
removes the task directory but not its usage history). Records used to live
under a `## Usage` heading in each ticket's blackboard region, but the
blackboard is composed into every launch prompt, so pure accounting history
bloated every future prompt on the ticket.

Schema 2 preserves the schema-1 identity and token fields: `ts`, `title`,
`slug`, `step`, `agent`, `cli`, `provider`, `model`, `session_id`, the four
token categories (`input_tokens`, `cache_creation_input_tokens`,
`cache_read_input_tokens`, `output_tokens`), and `usage_status` (`ok` |
`unknown`). It adds `started_at`, `ended_at`, `elapsed_seconds`, `human_turns`,
`agent_turns`, `request`, `outcome`, `content_status`, and `outcome_status`.
`ts` remains the session-end timestamp used by existing date filters. Old
schema-1 records remain readable; their activity fields are absent/null and
their token values roll up unchanged.

`outcome_status` describes process/session completion independently from token
parsing: `completed`, `failed`, `timed_out`, `interrupted`, or `unknown`.
`content_status` is `ok` or `unknown`. Keep the four token categories distinct:
coga composes large cached context layers, so cache tokens dominate and
collapsing them loses the most useful signal. All transcript parsing, bounded
content handling, and rollup logic lives in `src/coga/usage.py`; `launch.py`
and `commands/usage.py` stay thin.

## Capture — post-session, gated to agent sessions, never raises into launch

Capture runs in `spawn_agent_session`'s `finally` around the real agent
subprocess — **after** the session has exited (so it never races the agent's
own log appends) and **before** callers handle non-zero/timeout results. The
shared spawn path is deliberately the gate: ordinary task work, chained steps,
`coga chat`, `coga ticket`, project/onboarding interviews, and megalaunch all
emit exactly one record per agent process.

It is gated tightly:

- **Only real agent sessions.** Script iterations (Dream
  workers, autoclose, digest, skill-update — no transcript) and the
  `FileNotFoundError` spawn-failure path (no session ran) write **nothing**.
- **Never raises.** Missing or unparseable transcript data leaves the affected
  usage/content fields unknown/null, not an exception — capture can never break
  a launch.
- **Stateless identity stays explicit.** Bootstrap discussions are tagged with
  their bootstrap ref and title and `step: null`. Guided authoring remains
  `bootstrap/ticket` even when it composes against a real target task.

The record lands *past* the agent's final `bump`/`mark` sync, so the launch
teardown commits it immediately via `git.sync_log` — the log's own
conflict-free `merge=union` path (see `coga/sync`) — never via a catch-all
sweep of the working tree.

## Provider parser seam — both Claude and Codex are first-class

Matching is **never by file mtime.** Dispatch on the agent's `provider` (derived
from `agent.cli`); a configured cli that is neither `claude` nor `codex` returns
usage-unknown rather than crashing.

- **Claude** accepts `--session-id`. The seam is config, not a cli-name branch: a
  per-agent `session_id_flag` in `[agents.*]` (claude → `--session-id`, codex
  unset, mirroring `name_flag` so `build_agent_command` stays
  provider-agnostic). The loop mints a `uuid4` per iteration, passes
  `(session_id_flag, uuid)` into the command **and** the same uuid to capture,
  which reads exactly `~/.claude/projects/<cwd-hash>/<session-id>.jsonl` and
  **sums** `message.usage.*` over `assistant` lines (Claude reports per-message
  deltas), filtered to the session window by per-line `timestamp`.
  The pinned uuid is only materialised for a **fresh** session: a *resumed* one
  keeps appending to the transcript it resumed from, so that file never appears
  and usage would silently degrade to unknown. When the pinned path is missing,
  capture falls back to transcripts in the same `<cwd-hash>` project dir
  carrying a per-line `timestamp` inside the session window, and adopts the
  matched file's stem as the session id. Still never by mtime — a stray touch
  or a copy would forge it. Ambiguity is not resolved by guessing: two or more
  in-window transcripts in one cwd (concurrent sessions) → usage-unknown, the
  same no-mis-attribution rule the Codex path follows.
- **Codex** has no session-id flag, so capture snapshots the existing
  `~/.codex/sessions/**/rollout-*.jsonl` paths *before* spawn and claims the new
  file whose `session_meta.payload.cwd` matches (ambiguous / no-new-file →
  usage-unknown, never mis-attribution). Codex `token_count` events carry a
  **cumulative** `info.total_token_usage`, so take the **last** event — never sum
  — which makes resume/compaction double-counting a non-issue. Category mapping
  into the shared record: `cached_input_tokens` → cache-read, reasoning folded
  into output, cache-create left null (Codex exposes no create/read split).

## Bounded activity content — chronology, not a raw transcript

Activity extraction counts only timestamp-windowed, explicit human/user and
agent/assistant text. System/developer prompts, Coga's composed prompt,
launcher kickoff tokens such as `Begin`, tool calls, and tool results are
excluded. Claude user/assistant text blocks are read directly. For Codex, the
startup context before the first `turn_context` is injected context and is not
human activity; later user and assistant message items are the activity
surface.

`human_turns` and `agent_turns` count messages that contain explicit text after
those exclusions. `request` combines the human text in chronological order;
`outcome` is the last available assistant text. Each is whitespace-normalized
to one line and capped at 500 Unicode characters including a visible `…`
marker. Exact configured ticket-secret values are replaced with `[REDACTED]`
before truncation. If extraction or configured-secret redaction cannot complete
safely, the record still preserves timing, turn counts, identity, process
outcome, and any independently parsed tokens, but both content fields are null
and `content_status` is `unknown`.

Whole-session `elapsed_seconds` plus the explicit turn counts represent the
human/agent interaction honestly. Gaps between transcript events are not
typing measurements and are never labeled active human time.

## The read surface — `coga usage`

`coga usage` is the single accessor; consumers call it instead of re-parsing
transcripts or the log. It reads `coga/log.md`, parses only the tagged lines
whose message is a valid usage record (every other log line is skipped, not an
error), and totals them. It defaults to a **tokens-by-task** view (the
primary metric for a subscription team), also supports `--by model|agent|step`,
filters with `--since` / `--until` / `--task`, and emits `--json` for downstream
consumers. No dollar cost is computed — the team runs on a subscription, so
tokens-per-task is the question, not dollars (a price table is a deferred
follow-up).

## Durable history — accepted tradeoffs

Session records live in the append-only log, so they survive task
deletion/retirement and never ride a composed prompt. Pre-migration records
that lived in ticket `## Usage` sections were dropped rather than migrated
(history is reconstructible from the agent CLIs' own session files if ever
needed).

## What this context does NOT cover

- The git sync that commits the log append — see `coga/sync` (`sync_log`).
- The launch supervisor loop and the shared spawn path — see `coga/architecture`.
- The forbidden external telemetry / phone-home ban — see `coga/principles`.
