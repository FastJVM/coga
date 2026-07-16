---
name: coga/usage
description: How coga records and reads agent token usage — per-agent-session JSON records appended as tagged lines to the repo-global `coga/log.md` (no per-task store), the provider parser seam (Claude vs Codex), and `coga usage` as the single read surface. Local and committed, never a phone-home. Read before touching usage capture or adding a usage consumer.
---

# Agent Usage Tracking

Coga records the token usage of every agent session as plain committed text and
reads it back with `coga usage`. This is a foundational **local** data primitive
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

The record carries `ts`, `title`, `slug`, `step`, `agent`, `cli`, `provider`,
`model`, `session_id`, the four token categories (`input_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`),
`usage_status` (`ok` | `unknown`), and a `schema` version — so a line is
self-contained even though its log tag already names the task. Keep the four
categories distinct: coga composes large cached context layers, so cache tokens
dominate and collapsing them loses the most useful signal. All parsing and rollup
logic lives in `src/coga/usage.py`; `launch.py` and `commands/usage.py` stay
thin.

## Capture — post-session, gated to agent sessions, never raises into launch

Capture runs in `launch.py`'s `while True:` step loop, in the `finally` around
the agent subprocess — **after** the session has exited (so it never races the
agent's own log appends) and **before** the non-zero/timeout `sys.exit`, so
a session that burned tokens then died is still recorded. One record per loop
iteration, so chained steps and claude↔codex rotation each get their own line.

It is gated tightly:

- **Only real agent sessions.** Script iterations (Dream
  workers, autoclose, digest, skill-update — no transcript) and the
  `FileNotFoundError` spawn-failure path (no session ran) write **nothing**.
- **Never raises.** A missing or unparseable transcript appends a record with
  `usage_status: "unknown"` (tokens null), not an exception — capture can never
  break a launch.
- **Only real task launches.** Stateless bootstrap launches are not captured
  (`capture_usage` is off for them).

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
- **Codex** has no session-id flag, so capture snapshots the existing
  `~/.codex/sessions/**/rollout-*.jsonl` paths *before* spawn and claims the new
  file whose `session_meta.payload.cwd` matches (ambiguous / no-new-file →
  usage-unknown, never mis-attribution). Codex `token_count` events carry a
  **cumulative** `info.total_token_usage`, so take the **last** event — never sum
  — which makes resume/compaction double-counting a non-issue. Category mapping
  into the shared record: `cached_input_tokens` → cache-read, reasoning folded
  into output, cache-create left null (Codex exposes no create/read split).

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

Usage lives in the append-only log, so it survives task deletion/retirement
and never rides a composed prompt. Accepted consequences: stateless bootstrap
launches are never recorded, and pre-migration records that lived in ticket
`## Usage` sections were dropped rather than migrated (history is
reconstructible from the agent CLIs' own session files if ever needed).

## What this context does NOT cover

- The git sync that commits the log append — see `coga/sync` (`sync_log`).
- The launch supervisor loop and the shared spawn path — see `coga/architecture`.
- The forbidden external telemetry / phone-home ban — see `coga/principles`.
