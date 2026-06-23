---
title: track usage of LLM
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/architecture
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
step: 1 (implement)
---

## Description

Build **usage tracking**: a per-session record of LLM token usage for
every `relay launch`, accumulated as JSONL lines in each launched task's own
`blackboard.md` (no dedicated ledger file). This is a foundational data
primitive — its consumers are separate tickets: reporting (digest / dev-update),
agent autorouting (`autoroute-agent-based-on-remaining-usage`), and an
opportunistic "launch asks when there are free tokens" feature. This ticket
ships *only* the records and a way to read them (`relay usage`); it deliberately
does **not** define a budget cap or "remaining" — that belongs to the consumers.

Scope:

1. **Capture** — after a `relay launch` session ends, recover that
   session's token usage by parsing the agent's transcript. Relay launches
   agents as terminal-inheriting subprocesses, so usage cannot be streamed
   live; it is recovered after the session returns.
2. **Store** — append one JSONL usage record to the *launched task's own*
   `blackboard.md` under a `## Usage` section. No dedicated ledger file: the
   blackboards are the store, exactly like the digest task spools records into
   its own blackboard. The launch process already knows the task's
   title/slug/step/agent, so the record is self-describing and lands beside the
   work it describes — committed under `relay-os/` like every other Relay file.
3. **Read** — a `relay usage` command that globs the task (and recurring)
   blackboards, parses the `## Usage` records, and totals them (overall, by
   task, by model, by window). This is the single accessor the future
   report / autoroute / free-token tickets call, so none of them re-parse
   transcripts or blackboards themselves.

**Tokens only — no dollar cost.** This team runs on a Claude *subscription*,
not per-token API billing, so the question that matters is "which task burned
how many tokens," not "what did it cost in dollars." This ticket records and
reports the four token categories per task; it does **not** derive dollar cost.
Pricing (a price table + cost math) is deliberately out of scope and left to a
follow-up ticket if a dollar view is ever wanted.

## Acceptance Criteria

- A new module `src/relay/usage.py` holds all parsing and rollup logic.
  `launch.py` and `commands/usage.py` stay thin (call into it).
- After every `relay launch` **agent session** (one per `while True:` loop
  iteration in `launch.py` that actually spawns an agent CLI, not one per
  launch invocation), exactly one JSONL record is appended to the launched
  task's own `blackboard.md`, under a `## Usage` heading (created if absent).
  **There is no `relay-os/usage/` directory and no dedicated ledger file** —
  the task blackboards are the store.
  - **Only agent launches are recorded.** `mode: script` iterations (the loop
    runs a skill via `subprocess.run`, no claude/codex transcript — Dream
    workers, autoclose, digest, skill-update) write **no** record. A spawn that
    never started (the `FileNotFoundError` CLI-not-found path) writes no record
    either. "Session ran, transcript missing" is the only `usage_status:
    "unknown"` case; "no session ran" produces nothing.
  - Records are written for chained agent steps too (implement → peer-review →
    open-pr), each carrying its own `slug`, `step`, `agent`, `cli`, `model`.
  - A session that burned tokens and then exited non-zero is still recorded
    (capture runs in the `finally` around the subprocess call, which executes
    before launch.py's `sys.exit(exit_code)` non-zero/timeout early returns).
  - Capture never raises into the launch path: any failure to find/parse a
    transcript appends a record with `usage_status: "unknown"` (tokens null),
    not an exception. A launch with **no task blackboard** (stateless bootstrap
    shims) is skipped silently — a known, accepted gap (see Out of Scope).
  - Append is safe: capture runs after the session subprocess has exited, so it
    never races the agent's own writes to that blackboard.
  - `step` is recorded as the bare step **name** (parsed out of the ticket's
    `"N (name)"` form), read from the start-of-iteration ticket — i.e. the step
    the agent just ran, not the one it bumped to mid-session.
- Each record is a single self-describing JSON object on one line, with a
  `schema` version field and the shape pinned in Proposed Shape below. It
  carries `title` and `slug` so a record is attributable even though its
  location already implies the task.
- `relay usage` **defaults to a tokens-by-task view** (the primary metric for a
  subscription team). It globs `relay-os/tasks/**/blackboard.md` and
  `relay-os/recurring/**/blackboard.md`, parses only the valid JSON lines in
  each `## Usage` section (ignoring prose), and totals them. It also prints
  overall totals (four token categories) and supports `--by task|model|agent|step`.
  `--json` emits the same data as a structured object for downstream consumers;
  `--since` / `--until` / `--task` filter the rows. It is the only code path
  that reads usage back. No dollar cost is computed or shown.
- No transcript is matched by file mtime alone. Claude uses a minted session
  id; Codex uses a before/after new-file diff scoped by `cwd` (see Proposed
  Shape). Neither double-counts a resumed/append-only transcript, and an
  unrelated concurrent session in the same cwd is not mis-attributed.
- Codex sessions are parsed for real (not stubbed): a `relay launch` that runs
  `codex` produces a record with actual token counts, the codex `model`, and
  `provider: "openai"`. `usage_status: "unknown"` is the failure fallback only
  (transcript not found / unparseable), never the normal codex path.
- `pytest` covers **both** parsers (a synthetic Claude transcript → expected
  token sums; a synthetic Codex rollout → the final cumulative `total_token_usage`)
  and the rollup (by-task / by-model aggregation, mixed providers).
  `python -m pytest` and `relay validate --json` pass.

## Proposed Shape

**New module `src/relay/usage.py`** — the seam. Public surface:

- `@dataclass UsageRecord` with fields: `ts` (ISO-8601 UTC, session end),
  `title`, `slug`, `step` (str|None), `agent`, `cli`, `provider`,
  `model` (str|None), `session_id` (str|None), `input_tokens`,
  `cache_creation_input_tokens`, `cache_read_input_tokens`,
  `output_tokens` (each int|None), `usage_status` (`"ok"`|`"unknown"`),
  `schema` (int, start at `1`). `to_json()` / `from_json()` round-trip one
  JSONL line (the line that lives under `## Usage` in a blackboard).
- A **provider seam**: `parse_session(provider, *, cwd, session_id,
  pre_existing, window_start, window_end) -> ParsedUsage`. **Both
  `provider="claude"` and `provider="codex"` are implemented for real.**
  Dispatch on the agent's `provider` (derive from `agent.cli` name —
  `claude`/`codex`). `pre_existing` is the snapshot of session files captured
  before spawn (used by the codex matcher; see capture hook). A genuinely
  unfindable/unparseable transcript returns usage-unknown — that is the only
  unknown path for either provider. Dispatch is by `agent.cli` name; a
  configured agent whose cli is neither `claude` nor `codex` returns
  usage-unknown rather than crashing (no provider parser).
- Claude parser: resolve the transcript path
  `~/.claude/projects/<cwd-hash>/<session-id>.jsonl` where `<cwd-hash>` is the
  cwd with `/` and `.` replaced by `-` (verified against the live layout).
  Sum `message.usage.*` over `type=="assistant"` lines, taking `model` from
  the lines. Filter lines to the session window by per-line `timestamp` as a
  guard even when the file is session-scoped. (Per-line summing because Claude
  reports per-message deltas.)
- Codex parser (verified against the live `~/.codex/sessions/` layout): session
  rollouts live at `~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<ISO>-<uuid>.jsonl`.
  Codex has no `--session-id` to pin, so identify the session by **new-file
  diff**: the rollout file(s) that did not exist in `pre_existing` and whose
  first-line `session_meta.payload.cwd == cwd` is this session (newest wins on
  ties). Unlike Claude, codex's `event_msg`→`token_count` events carry a
  **cumulative** `info.total_token_usage`, so take the **last** such event's
  totals — do not sum, which also makes resume/compaction double-counting a
  non-issue. `model` comes from `turn_context.payload.model` (e.g. `gpt-5.4`);
  `provider` from `session_meta.payload.model_provider` (e.g. `openai`).
  Token-category mapping into the shared record: `input_tokens`→`input_tokens`,
  `cached_input_tokens`→`cache_read_input_tokens`,
  `output_tokens + reasoning_output_tokens`→`output_tokens` (reasoning tokens
  are billed output; fold them in), `cache_creation_input_tokens`→`None`
  (codex exposes no create-vs-read split). Keep the four-category record shape
  provider-agnostic.
- `append_record(blackboard: Path, record: UsageRecord) -> None` — append the
  record's JSONL line to the given `blackboard.md` under a `## Usage` heading
  (create the heading at EOF if missing; otherwise append beneath the existing
  one). Atomic via `atomicio`. Touches only that section — never reflows the
  rest of the blackboard.
- `load_records(relay_os: Path) -> list[UsageRecord]` — glob
  `relay-os/tasks/**/blackboard.md` and `relay-os/recurring/**/blackboard.md`,
  scan each `## Usage` section, `from_json` every line that parses as a usage
  record, skip anything that doesn't (prose, stray lines). Robust to a human or
  agent having edited prose elsewhere in the file.
- `rollup(records, *, by=None, since=None, until=None, task=None) -> Rollup` —
  pure aggregation behind `relay usage`. No summary file is written; `relay
  usage` is the read surface.

**Per-provider session matching (resolves the matching/double-count risk).**
Two deterministic strategies, one per provider, both behind the seam — never
assume every CLI behaves alike:

- **Claude** accepts `--session-id <uuid>`. Wire this through config, not a
  cli-name branch (matching how `name_flag` already works — `build_agent_command`
  stays provider-agnostic): add a per-agent `session_id_flag` to
  `relay.toml [agents.*]` (`claude` → `"--session-id"`, codex leaves it unset).
  The `while True:` loop mints a fresh `uuid4` per iteration; when the step's
  agent has a `session_id_flag`, it passes `(session_id_flag, uuid)` into
  `build_agent_command` (inserted alongside the existing name/​skip argv) **and**
  hands the same uuid to `capture_session`, so capture reads exactly that
  transcript file. An agent with no `session_id_flag` mints nothing and relies on
  its own matcher (codex's new-file diff). Touches the `[agents.*]` config schema,
  so update the config loader, the `example/` fixture, and add a test.
- **Codex** has no such flag, so capture snapshots the set of existing
  `~/.codex/sessions/**/rollout-*.jsonl` paths *before* spawning and passes it
  as `pre_existing`; the parser takes the new file with a matching `cwd`. (A
  resumed codex session appends to its existing file rather than creating a new
  one; the cumulative-totals read still gives the correct session total, and
  the new-file diff degrades to "no new file" → usage-unknown rather than
  mis-attribution.)

**Capture hook in `launch.py`** (the `while True:` loop, ~418–448):

- Before spawning, record `window_start` (wall clock) and, per provider, the
  match key: the minted `session_id` (claude), or the `pre_existing` snapshot
  of `~/.codex/sessions/**/rollout-*.jsonl` paths (codex). Snapshotting is a
  cheap `glob` and only done for the provider being launched.
- The subprocess call already sits in a `try/…/finally` (the `finally`
  currently runs `_cleanup_prompt()`). Add the capture call there, next to
  `_cleanup_prompt()` — this `finally` executes before every downstream exit
  path (the timeout `sys.exit`/`return "timeout"` and the non-zero
  `sys.exit(exit_code)` both come after it), so a session that burned tokens
  then died is still captured. It calls a single thin helper
  `usage.capture_session(...)` with the task's `blackboard` path, `title`,
  `slug`, `step` name, `agent`, `cli`, `provider`, `session_id`/`pre_existing`,
  `window_start`, `window_end=now`. The helper parses the transcript, builds the
  record, and appends one line under `## Usage` in that blackboard, swallowing
  all exceptions (log to stderr) so capture can never break a launch.
- **Capture only for agent sessions.** Gate the call so it fires only when this
  iteration spawned an agent CLI (`mode in {interactive, auto}`), never for
  `mode: script` iterations (no transcript exists) and never on the
  `FileNotFoundError` spawn-failure path (no session ran). If no blackboard path
  is available (stateless bootstrap shim), it no-ops.
- One record per agent loop iteration ⇒ chained steps and agent rotations each
  get their own entry, all appended to the same task blackboard.

**New command `src/relay/commands/usage.py`** registered in `cli.py` as
`relay usage`. Thin Typer entrypoint: options `--by`
(`task|model|agent|step`, **default `task`**), `--since`, `--until`, `--task`,
`--json`. Loads records via `usage.load_records` (which scans the blackboards),
calls `usage.rollup`, prints a table (human; the four token categories + total)
or `json.dumps` (machine). No parsing logic in the command.

**Order of work:** (1) `usage.py` record + rollup + **both** parsers (Claude
per-message sum; Codex last-cumulative), with unit tests on synthetic
transcript fixtures for each, plus `append_record`/`load_records` round-trip
through a `## Usage` blackboard section. (2) `relay usage` command + tests.
(3) launch.py capture hook (gated to agent sessions) + per-provider matching
(claude `session_id_flag` minting; codex pre-spawn rollout snapshot), appending
to the task blackboard; add `session_id_flag` to the `[agents.*]` config schema +
`example/` fixture. (4) `relay validate --json`, update `example/` only if
task/layout semantics change (they should not).

## Out of Scope

- Dollar cost / pricing — no price table, no `cost_usd`, no cost math. The team
  is on a subscription; tokens are the metric. A dollar view is a follow-up
  ticket if ever wanted.
- **The `refresh-hardcoded-data` recurring sweep — split to a follow-up ticket.**
  Shipping it means a recurring template + a `maintenance/refresh` workflow +
  a `mode: script` skill that posts the Slack reminder (`mode: auto` is
  temporarily frozen, so the digest `mode: script` pattern is the only viable
  shape) + `update.py` vendoring wiring (`VENDORED_RECURRING_TEMPLATES`,
  `VENDORED_WORKFLOW_TEMPLATES`, `VENDORED_SKILL_TEMPLATES`) + packaging tests —
  a full shipped battery. Kept out so this ticket stays the usage primitive.
  The seeded first chore ("verify the Claude + Codex transcript parsers in
  `usage.py` still match the live `~/.claude` / `~/.codex` formats" — the
  parsers hardcode transcript paths and JSONL field names that drift on CLI
  updates) carries to that follow-up.
- Budget caps, "remaining" tokens, and any enforcement — consumer tickets
  (`autoroute-agent-based-on-remaining-usage`, the free-token launcher).
- Autorouting decisions and the opportunistic "launch when tokens are free"
  feature.
- Wiring usage totals into digest / dev-update output.
- A dedicated ledger/summary file under `relay-os/usage/` — dropped. Usage lines
  live in each task's own `blackboard.md` (`## Usage`); `relay usage` is the
  read surface. No committed global rollup file.
- Auto-committing usage to git — capture leaves the blackboard write in the
  working tree for the normal commit flow; `relay launch` adds no git side
  effects.
- **Usage for stateless bootstrap launches** (e.g. `bootstrap/ticket`,
  `bootstrap/orient`) — those have no persistent task blackboard, so their
  sessions are not recorded. Accepted gap; if it matters later, a central spool
  is the follow-up.
- **Usage history is task-scoped** — retiring/deleting a task directory removes
  its usage lines with it. Accepted: usage lives beside the work, not in a
  durable central ledger.

## Implementation Notes (from ticket author)

**Where it lives.** Relay is markdown-first and git-backed — there is no
database and no daemon. Usage is plain committed text, not hidden state, and
not a new file type: each session appends one JSONL line under a `## Usage`
heading in the *launched task's own* `blackboard.md`. This mirrors the digest
task, which already spools JSONL records into its blackboard's `## Spool`
section and parses them back with a script (`relay digest`). `relay usage` is
the equivalent reader here. The JSONL record is the contract the consumer
tickets read, so keep it self-describing (carry `title`/`slug`).

**Where capture hooks in (read this carefully).** `src/relay/commands/launch.py`
runs the agent via `run_with_done_marker` (interactive) or `subprocess.run`
(script/auto) around line 418–435 — but that call sits **inside a `while True:`
step-chaining loop** (≈lines 334–467). A single `relay launch` can spawn
**multiple** sessions in one process: implement → peer-review → open-pr,
rotating between claude and codex. So:

- Record **one usage line per loop iteration (per session)**, not one per
  launch. Each line should carry title, slug, step, agent/CLI, and model —
  these differ across iterations within the same launch.
- Place capture in a `finally` around the subprocess call so a session that
  **burned tokens then exited non-zero** is still recorded. Note launch.py
  does `sys.exit(exit_code)` on non-zero exit (≈442–448) before the loop
  re-reads state — capture must run before that early exit, not after.
- A single supervised run can legitimately produce a **Codex** session
  (claude↔codex rotation across steps), so the codex parser is a first-class
  deliverable here — both providers must produce real token records from one
  launch.

Keep the command entrypoint thin (per `relay/codebase`) — put the
parsing/rollup logic in a new module (e.g. `src/relay/usage.py`), not in
`launch.py`.

**Transcript source (Claude).** Claude Code writes per-message JSONL to
`~/.claude/projects/<cwd-hash>/<session-id>.jsonl`. Each assistant line
carries `usage` (`input_tokens`, `cache_creation_input_tokens`,
`cache_read_input_tokens`, `output_tokens`), `model`, and `sessionId`.
Keep the four token categories distinct in the record (cache-create vs
cache-read vs base input vs output) — Relay composes large cached context
layers, so cache tokens dominate and collapsing them loses the most useful
signal. No dollar cost is derived (out of scope).

**Transcript source (Codex).** Codex writes a per-session rollout JSONL to
`~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<ISO>-<uuid>.jsonl` (verified
against the live tree). The first line is `session_meta` (`payload.id`,
`payload.cwd`, `payload.model_provider`); `turn_context` lines carry
`payload.model`; `event_msg`→`token_count` events carry a **cumulative**
`info.total_token_usage` (`input_tokens`, `cached_input_tokens`,
`output_tokens`, `reasoning_output_tokens`, `total_tokens`). Take the **last**
`token_count` event as the session total — don't sum. Map into the shared
four-category record: `cached_input_tokens`→cache-read, reasoning folded into
output, cache-create left null (codex has no split).

**Transcript matching & double-counting (the likely-bug zone).** Don't match
transcripts by file mtime alone. Each provider has a deterministic key:
**claude** = minted `--session-id`; **codex** = the rollout file that appears
in `~/.codex/sessions/**` *after* spawn (snapshot before, diff after) with a
matching `session_meta.cwd`. Claude reports per-message deltas → sum lines,
filtered by per-line `timestamp` to the session window. Codex reports a running
cumulative → just read the last `total_token_usage`, so resume/compaction never
double-counts. Guard against a second unrelated session in the same cwd: claude
by exact session id, codex by the new-file diff (an already-existing file is
never claimed).

**Robustness.** Capture must never break a launch. If the transcript
can't be found or parsed, still write a record with usage marked unknown
(and log it), rather than raising.

**Out of scope (separate tickets):** budget caps / "remaining" tokens,
autorouting decisions, the free-token opportunistic launcher, and wiring
totals into digest output. Build the primitive and the read command; let
the consumers consume.

**Tests / fixtures.** Add pytest coverage for **both** parsers and the rollup:
a synthetic Claude transcript (per-message deltas → summed) and a synthetic
Codex rollout (cumulative `total_token_usage` → last-event read), each asserted
to the expected usage record, plus an `append_record`→`load_records` round-trip
through a `## Usage` blackboard section and a mixed-provider rollup. Per
CLAUDE.md, update `example/` fixtures if launch/task layout semantics change.
Run `python -m pytest` and `relay validate --json` before the PR.
