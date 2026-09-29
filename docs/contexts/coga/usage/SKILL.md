---
name: coga/usage
description: Where Coga's agent-session usage records live (tagged JSON lines in the repo-global `coga/log.md`, git-synced like the rest of the log) and how `coga usage` and `src/coga/usage.py` read them back as token rollups; capture and the record schema are `coga/internals/activity-capture`.
---

# Agent session usage

Every Coga-launched agent session appends one usage record to the repo's own
`coga/log.md`, and `coga usage` rolls those records up. This is a local,
git-backed data primitive: the records live in the repository and travel
wherever the repository's git remote sends them — Coga's state publication
pushes `coga/log.md` to the control branch (`coga/sync`). Session activity and
token records are excluded from the weekly aggregate telemetry snapshot;
[`coga/telemetry`](../telemetry/SKILL.md) owns that separate external boundary.

Consumers (agent autorouting, report views) are separate work. This primitive
ships the records and the reader and deliberately defines no budget cap, no
"remaining", and no dollar cost (the team runs on a subscription, so tokens
per task is the question; a price table is a deferred follow-up).

How a record is captured, matched to a provider transcript, and bounded is
[`coga/internals/activity-capture`](../internals/activity-capture/SKILL.md).

## The store — tagged lines in `coga/log.md`

There is no `coga/usage/` directory, no ledger file, and no per-task store.
Each record is an ordinary log line written through
`usage.append_record` → `logfile.append_log`:

```
YYYY-MM-DD HH:MM [<task-ref>] [system] {"schema": 2, ...}
```

- The log is append-only and `merge=union`, so concurrent sessions never
  conflict (`coga/internals/spool-merge`).
- The log is never a prompt-composition layer. Records used to live under a
  `## Usage` blackboard heading, which bloated every later prompt on the
  ticket; they moved to the log, and the old blackboard records were dropped
  rather than migrated.
- The log outlives the task: `coga delete` and `coga retire` remove the task
  directory but not its usage history.

## The read API — `coga usage` and `src/coga/usage.py`

`coga usage` is the single accessor; consumers call it (or
`usage.load_records` plus `usage.rollup`) instead of re-parsing the log or
transcripts. `load_records` reads `coga/log.md` and keeps only lines whose
message parses as a schema 1 or 2 record; every other line is skipped, not an
error.

- `--by task|model|agent|step` groups rows (default `task`); a record with no
  value for the key groups under `(unknown)`. Any other value exits 2.
- `--since` / `--until` take an ISO timestamp or a bare `YYYY-MM-DD` (which
  covers the whole day at either end); they filter on `ts`, the session-end
  time. An unparseable value exits 2.
- `--task <slug>` is an exact slug match, not the prefix matching
  `launch`/`show`/`bump` accept.
- `--json` emits the same rollup as one object.

The table prints an `Overall:` line and one row per group with sessions,
unknown, total, input, cache_create, cache_read, and output tokens. The four
token categories stay distinct because Coga's composed context makes cache
tokens dominate. `unknown` counts sessions whose usage could not be
attributed; they count as sessions but contribute zero tokens, so a high
unknown count means the totals are a floor, not a measurement.

`coga usage` is read-only: no mutation, no network, and it is in
`cli._NON_SWEEPING_COMMANDS`, so it never triggers the end-of-command state
sweep. It is the after-the-fact counterpart to `coga launch --prompt-report`,
which estimates the prompt side before a run.

## Reading the numbers honestly

- `elapsed_seconds` is whole-session wall time. It is not active human time,
  and gaps between transcript events are not typing measurements.
- `human_turns` / `agent_turns` count explicit messages only.
- Sessions observed in the same window are workstreams, not proof of
  simultaneous processes or a productivity multiplier. The dated analysis
  built on these records is `docs/evidence/velocity.md`.

## Facts a future price table needs

No pricing is implemented. These facts about the records were verified while a
dollar-cost proxy was scoped and set aside; any price table must handle them
rather than rediscover them.

- **Claude cache writes mix two rates.** Claude transcripts carry
  `usage.cache_creation.{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}`,
  but `_parse_claude_session` keeps only the combined
  `cache_creation_input_tokens`, so a record cannot tell which write rate
  applied. Both TTLs occur in practice and the two rates differ, so no single
  rate is both exact and a guaranteed lower bound. A dated one-machine survey
  of the mix is `docs/evidence/claude-cache-ttl-survey.md`.
- **A Codex `cache_creation_input_tokens: null` means "no split exposed", not
  "no charge".** OpenAI charges cache writes on GPT-5.6-and-later models, and
  `_parse_codex_rollout` subtracts only cached-read tokens from input, so any
  writes stay inside the `input_tokens` bucket.
- **Context-length tiers are invisible.** Providers price long-context
  requests at higher tiers, and records do not say which tier applied.
- **A session's tokens go to its last model.** `_parse_claude_session` sums
  usage across every assistant line but records only the last model seen, so
  a session that switches models attributes all of its tokens to the final
  one.
