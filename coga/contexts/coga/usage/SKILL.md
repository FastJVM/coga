---
name: coga/usage
description: How coga records and reads agent token usage — per-agent-session JSONL records appended to each task's own blackboard (no central ledger), the provider parser seam (Claude vs Codex), and `coga usage` as the single read surface. Local and committed, never a phone-home. Read before touching usage capture or adding a usage consumer.
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

## The store — each task's own blackboard, no central ledger

There is **no `coga/usage/` directory and no dedicated ledger file.** Each agent
session appends exactly one self-describing JSONL record under a `## Usage`
heading in the *launched task's own* `ticket.md` blackboard region (created if
absent), mirroring how the digest task spools records into its own file. The
record carries `ts`, `title`, `slug`, `step`, `agent`, `cli`, `provider`,
`model`, `session_id`, the four token categories (`input_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`),
`usage_status` (`ok` | `unknown`), and a `schema` version — so a line is
attributable even though its location already implies the task. Keep the four
categories distinct: coga composes large cached context layers, so cache tokens
dominate and collapsing them loses the most useful signal. All parsing and rollup
logic lives in `src/coga/usage.py`; `launch.py` and `commands/usage.py` stay
thin.

## Capture — post-session, gated to agent sessions, never raises into launch

Capture runs in `launch.py`'s `while True:` step loop, in the `finally` around
the agent subprocess — **after** the session has exited (so it never races the
agent's own blackboard writes) and **before** the non-zero/timeout `sys.exit`, so
a session that burned tokens then died is still recorded. One record per loop
iteration, so chained steps and claude↔codex rotation each get their own line.

It is gated tightly:

- **Only real agent sessions** (`mode: agent`). `mode: script` iterations (Dream
  workers, autoclose, digest, skill-update — no transcript) and the
  `FileNotFoundError` spawn-failure path (no session ran) write **nothing**.
- **Never raises.** A missing or unparseable transcript appends a record with
  `usage_status: "unknown"` (tokens null), not an exception — capture can never
  break a launch.
- **No task blackboard** (stateless bootstrap launches) → silent skip.

Capture leaves the write in the working tree; `coga launch` adds no git side
effect of its own. The per-session `## Usage` record is committed later by the
`sync_coga_state` catch-all sweep (see `coga/sync`).

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
transcripts or blackboards. It globs `coga/tasks/**` and `coga/recurring/**`
blackboards, parses only the valid JSON lines in each `## Usage` section
(ignoring prose), and totals them. It defaults to a **tokens-by-task** view (the
primary metric for a subscription team), also supports `--by model|agent|step`,
filters with `--since` / `--until` / `--task`, and emits `--json` for downstream
consumers. No dollar cost is computed — the team runs on a subscription, so
tokens-per-task is the question, not dollars (a price table is a deferred
follow-up).

## Task-scoped — accepted tradeoffs

Usage lives beside the work, not in a durable central ledger, with two accepted
consequences: deleting/retiring a task directory removes its usage lines with it,
and stateless bootstrap launches (no persistent blackboard) are never recorded.
If a durable cross-task rollup is ever needed, a central spool is the follow-up.

## What this context does NOT cover

- The git sync that commits the `## Usage` write — see `coga/sync`
  (`sync_coga_state`).
- The launch supervisor loop and the shared spawn path — see `coga/architecture`.
- The forbidden external telemetry / phone-home ban — see `coga/principles`.
