---
name: coga/internals/activity-capture
description: How Coga captures one bounded, secret-redacted usage record per agent session — the schema-2 record fields, the post-session capture point and its gates, Claude versus Codex transcript matching and token counting, and why ambiguity yields unknown rather than a guess.
---

# Session activity capture

The read side and store are [`coga/usage`](../../usage/SKILL.md). This page
owns what is written and how it is derived. All parsing, bounding, and rollup
logic lives in `src/coga/usage.py`; `commands/launch.py` and
`commands/usage.py` stay thin.

## Record schema (`USAGE_SCHEMA = 2`)

Identity and tokens (unchanged from schema 1): `ts` (session end, used by
date filters), `title`, `slug`, `step`, `agent`, `cli`, `provider`, `model`,
`session_id`, `input_tokens`, `cache_creation_input_tokens`,
`cache_read_input_tokens`, `output_tokens`, `usage_status` (`ok` | `unknown`).

Activity (schema 2): `started_at`, `ended_at`, `elapsed_seconds`,
`human_turns`, `agent_turns`, `request`, `outcome`, `content_status` (`ok` |
`unknown`), and `outcome_status` (`completed`, `failed`, `timed_out`,
`interrupted`, `unknown`). `outcome_status` describes the process, independent
of token parsing. `usage_reason` carries the parser's reason when
`usage_status` is `unknown` (the same text capture prints to stderr) and is
null otherwise; it was added without a schema bump, so records written before
it read back with it null. Schema-1 records stay readable with activity fields
null and roll up unchanged.

## Capture point and gates

`usage.capture_session` runs in the `finally` of
`commands/launch.py` `spawn_agent_session`, after the agent process exits (so
it never races the agent's own log appends) and before callers handle
non-zero or timeout results. Because every agent launch goes through that
shared spawn path (`coga/internals/agent-spawn`), ordinary steps, chained
steps, `coga chat`, `coga ticket`, `coga build` and other bootstrap sessions,
and megalaunch children each emit exactly one record.

- **Agent sessions only.** Deterministic scripts and recipes (Dream workers,
  autoclose, skill-update) have no transcript and write nothing; neither does
  a spawn that failed to start (`FileNotFoundError`).
- **Never raises.** A missing or unparseable transcript, or an append
  failure, becomes a stderr note and unknown/null fields; capture cannot
  break a launch.
- **Stateless identity stays explicit.** Bootstrap sessions are tagged with
  their bootstrap ref and title and `step: null`; guided authoring stays
  `bootstrap/ticket` even when composed against a real target task.
- The record lands after the agent's final `bump`/`mark` sync, so teardown
  publishes exactly the log through `git.sync_log` (its union-safe path),
  never a broad sweep.

## Provider matching — never by file mtime

**Launch marker.** `spawn_agent_session` mints a fresh `uuid4` per spawn and
ends the prompt with the line `coga-launch: <uuid>`
([prompt composition](../../prompt-composition/SKILL.md#launch-marker)),
passing the same value to capture as `launch_marker`. It is only a
tie-breaker: when more than one candidate survives a provider's ordinary
filters, capture keeps the candidates whose own message text carries that
exact line and accepts exactly one. Zero or several marked candidates stay
unknown. Only message text counts, never tool calls or results, so a session
that saw a sibling's argv (for example via `ps`) cannot claim it.

`usage.parser_key_for_cli` maps the agent's `cli` basename to `claude` or
`codex`; any other CLI records `provider: unknown` with usage unknown.

**Claude** (per-message deltas, **summed**). The agent config's
`session_id_flag` (claude: `--session-id`; codex: unset, mirroring
`name_flag`) keeps `build_agent_command` provider-agnostic. Each iteration
mints a `uuid4`, passes it to the CLI and to capture, which reads
`~/.claude/projects/<cwd-hash>/<session-id>.jsonl` and counts
`message.usage.*` once per `message.id` among `assistant` lines whose
`timestamp` falls inside the session window. The last in-window line for each
ID supplies its usage, including any updated streaming output count; lines
without a message ID count individually. A resumed session keeps writing to
the transcript it resumed from, so the pinned file may not exist; capture
then considers transcripts in
the same project directory with a per-line `timestamp` in the window and
adopts the match's stem as `session_id`. Two or more in-window candidates
(a resume plus a concurrent session in one cwd) are narrowed to those with an
in-window `user` line carrying the launch marker; otherwise usage is
unknown. A discussion launch (`coga chat`, `coga ticket`) passes its prompt
through `--append-system-prompt`, so the marker never reaches the transcript
and that case stays unknown.

**Provably empty.** When the pinned transcript itself exists but has no
in-window assistant usage, the session never reached the API: the record is
`ok` with all four token counts zero. This applies only to the pinned file; a
fallback candidate with no usage proves nothing about this launch and stays
unknown, and a missing Codex rollout is never treated as zero (absence is not
proof).

Claude model attribution takes the last non-`<synthetic>` model, falling back
to `<synthetic>` when that is the only model present. Synthetic assistant
lines still contribute all token counts; sessions that switch real models
remain attributed to the last real model.

**Codex** (cumulative counts, **last event**). With no session-id flag,
capture snapshots `~/.codex/sessions/**/rollout-*.jsonl` before spawn and
claims the one new file whose `session_meta.payload.cwd` equals the session
cwd (and whose start time is in the window). Subagent rollouts are skipped
first: every codex child writes its own rollout with the parent's cwd, so a
rollout whose `session_meta.payload` has `thread_source == "subagent"` or a
non-empty `parent_thread_id` never matches. A parent plus N children resolves
to the parent; subagent tokens are deliberately not counted (parity with a
parent-only session). Several top-level matches (concurrent launches in one
cwd) are narrowed to the one whose `user` or `developer` `response_item`
message carries the launch marker: an ordinary prompt is a user message after
codex's own AGENTS.md/environment user message, a discussion prompt is a
developer message. None, or several after the tie-break (a child-only set
included) → usage unknown. A resumed rollout predates the pre-spawn snapshot
and is never a candidate, so a resumed Codex session stays unknown. `token_count` events carry cumulative `info.total_token_usage`, so the
last event is taken and never summed, which makes resume and compaction
double-counting a non-issue. Mapping: `cached_input_tokens` → cache-read,
reasoning folded into output, cache-create null (Codex exposes no split).

Ambiguity is never resolved by guessing: mis-attributing tokens is worse than
an unknown row.

## Bounded, redacted activity content

Only explicit human/user and agent/assistant text inside the window counts.
System/developer prompts, Coga's composed prompt, launcher kickoff text such
as `Begin`, tool calls, and tool results are excluded. For Codex, startup
context before the first `turn_context` is injected, not human activity.

- `human_turns` / `agent_turns` count messages with explicit text left after
  those exclusions.
- `request` joins the human text in order; `outcome` is the last assistant
  text.
- Exact configured ticket-secret values are replaced with `[REDACTED]` (longest
  first) before whitespace is normalized to one line and the text is capped
  at `MAX_ACTIVITY_CHARS` (500) including the `…` marker.
- If extraction or redaction cannot complete safely (including when the secret
  values could not be resolved), `request` and `outcome` are null and
  `content_status` is `unknown`; timing, turn counts, identity, process
  outcome, and independently parsed tokens are kept.

`elapsed_seconds` is whole-session wall time; together with the turn counts it
describes the interaction honestly. It is never labeled active human time.
