---
title: track usage of LLM
status: paused
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Build a **usage ledger**: a per-session record of LLM token usage (and
derived cost) for every `relay launch`, accumulated into a file under
`relay-os/`. This is a foundational data primitive — its consumers are
separate tickets: reporting (digest / dev-update), agent autorouting
(`autoroute-agent-based-on-remaining-usage`), and an opportunistic
"launch asks when there are free tokens" feature. This ticket ships
*only* the ledger and a way to read it; it deliberately does **not**
define a budget cap or "remaining" — that belongs to the consumers.

Scope:

1. **Capture** — after a `relay launch` session ends, recover that
   session's token usage by parsing the agent's transcript and append one
   record to the ledger. Relay launches agents as terminal-inheriting
   subprocesses, so usage cannot be streamed live; it is recovered after
   the session returns.
2. **Store** — append-only machine ledger plus a rolled-up
   human-readable summary, both committed under `relay-os/` like every
   other Relay file.
3. **Read** — a `relay usage` command that totals the ledger (overall,
   by task, by model, by window). This is the single accessor the future
   report / autoroute / free-token tickets call, so none of them re-parse
   transcripts themselves.

## Acceptance Criteria

- A new module `src/relay/usage.py` holds all parsing, pricing, and rollup
  logic. `launch.py` and `commands/usage.py` stay thin (call into it).
- After every `relay launch` *session* (one per `while True:` loop iteration
  in `launch.py`, not one per launch invocation), exactly one record is
  appended to `relay-os/usage/ledger.jsonl`.
  - Records are written for chained steps too (implement → peer-review →
    open-pr), each carrying its own `slug`, `step`, `agent`, `cli`, `model`.
  - A session that burned tokens and then exited non-zero is still recorded
    (capture runs in a `finally`, before launch.py's `sys.exit(exit_code)`).
  - Capture never raises into the launch path: any failure to find/parse a
    transcript yields a record with `usage_status: "unknown"` (tokens null),
    not an exception.
- Each ledger record is a single self-describing JSON object with a `schema`
  version field and the shape pinned in Proposed Shape below.
- Token cost is derived from `model` + a per-category price table (base input,
  cache-create, cache-read, output priced separately). An unpriced model
  yields `cost_usd: null` (tokens still recorded) — never a silent `0`.
- `relay usage` prints overall totals (four token categories + total cost) and
  by-model / by-task breakdowns; `--json` emits the same data as a structured
  object for downstream consumers; `--since` / `--until` / `--task` filter the
  rows. It is the only code path that reads the ledger.
- `relay-os/usage/summary.md` holds a human-readable rollup regenerated from
  the ledger on capture (the committed report surface).
- No transcript is matched by file mtime alone. Within a session window the
  per-line `timestamp` (or a minted session id, see Proposed Shape) scopes
  which `usage` lines count, so a resumed/append-only transcript is not
  double-counted and an unrelated concurrent session in the same cwd is not
  mis-attributed.
- Codex sessions produce a record (`usage_status: "unknown"` is acceptable for
  the stub) rather than crashing or being attributed Claude usage.
- `pytest` covers the parser (synthetic transcript → expected token sums),
  the price table (per-category cost math + unknown-model → null), and the
  rollup. `python -m pytest` and `relay validate --json` pass.

## Proposed Shape

**New module `src/relay/usage.py`** — the seam. Public surface:

- `@dataclass UsageRecord` with fields: `ts` (ISO-8601 UTC, session end),
  `slug`, `step` (str|None), `agent`, `cli`, `provider`, `model` (str|None),
  `session_id` (str|None), `input_tokens`, `cache_creation_input_tokens`,
  `cache_read_input_tokens`, `output_tokens` (each int|None), `cost_usd`
  (float|None), `usage_status` (`"ok"`|`"unknown"`), `schema` (int, start at
  `1`). `to_json()` / `from_json()` round-trip one JSONL line.
- A **provider seam**: `parse_session(provider, *, transcript_dir, cwd,
  session_id, window_start, window_end) -> ParsedUsage`. `provider="claude"`
  is implemented; `provider="codex"` returns usage-unknown. Dispatch on the
  agent's `provider` (derive from `agent.cli` name — `claude`/`codex`).
- Claude parser: resolve the transcript path
  `~/.claude/projects/<cwd-hash>/<session-id>.jsonl` where `<cwd-hash>` is the
  cwd with `/` and `.` replaced by `-` (verified against the live layout).
  Sum `message.usage.*` over `type=="assistant"` lines, taking `model` from
  the lines. Filter lines to the session window by per-line `timestamp` as a
  guard even when the file is session-scoped.
- `PRICES`: module-level `dict[str, dict[str, float]]` — per-model, per-token-
  category USD-per-token (or per-Mtok) rates, with an "as of <date>" comment.
  `cost(model, tokens) -> float|None` returns `None` for an unpriced model.
- `append_record(relay_os: Path, record: UsageRecord) -> None` — append one
  JSONL line to `relay-os/usage/ledger.jsonl` (atomic, via `atomicio`).
- `load_records(relay_os) -> list[UsageRecord]` and
  `rollup(records, *, by=None, since=None, until=None, task=None) -> Rollup`
  — pure aggregation used by both `summary.md` regeneration and `relay usage`.
- `write_summary(relay_os) -> None` — regenerate `usage/summary.md` from the
  ledger.

**Session-id capture (resolves the matching/double-count risk).** `claude`
accepts `--session-id <uuid>`. In `build_agent_command` (launch.py), for the
claude provider mint a `uuid4` per session and pass `--session-id <that>`,
returning it to the loop so capture reads exactly that transcript file. This
turns transcript matching from a fragile mtime/window heuristic into a
deterministic lookup. Codex has no equivalent flag today → its records are
usage-unknown until a Codex parser lands. Keep the minting behind the provider
seam; never assume every CLI takes the flag.

**Capture hook in `launch.py`** (the `while True:` loop, ~418–448):

- Before spawning, record `window_start` (wall clock) and the minted
  `session_id` (claude) / `None` (codex).
- Wrap the subprocess call's existing `try/finally` so that in the `finally`
  — after `_cleanup_prompt()`, before the `sys.exit(exit_code)` non-zero
  early return — it calls a single thin helper
  `usage.capture_session(...)` with the step's `slug`, `step` name, `agent`,
  `cli`, `provider`, `session_id`, `window_start`, `window_end=now`. The
  helper builds and appends the record and regenerates `summary.md`, swallowing
  all exceptions (log to stderr) so capture can never break a launch.
- One record per loop iteration ⇒ chained steps and agent rotations each get
  their own entry.

**New command `src/relay/commands/usage.py`** registered in `cli.py` as
`relay usage`. Thin Typer entrypoint: options `--by`
(`task|model|agent|step`), `--since`, `--until`, `--task`, `--json`. Loads
records via `usage.load_records`, calls `usage.rollup`, prints a table
(human) or `json.dumps` (machine). No ledger parsing logic in the command.

**Order of work:** (1) `usage.py` record + Claude parser + price table +
rollup, with unit tests on a synthetic transcript fixture. (2) `relay usage`
command + tests. (3) launch.py capture hook + session-id minting. (4)
`summary.md` regeneration. (5) `relay validate --json`, update `example/` only
if task/layout semantics change (they should not).

## Out of Scope

- Budget caps, "remaining" tokens, and any enforcement — consumer tickets
  (`autoroute-agent-based-on-remaining-usage`, the free-token launcher).
- Autorouting decisions and the opportunistic "launch when tokens are free"
  feature.
- Wiring usage totals into digest / dev-update output.
- A full Codex transcript parser — Codex is stubbed at usage-unknown behind
  the provider seam this ticket builds.
- Auto-committing the ledger to git (open question; default is to leave the
  write in the working tree for the normal commit flow).

## Implementation Notes (from ticket author)

**Where it lives.** Relay is markdown-first and git-backed — there is no
database and no daemon. The ledger must be plain committed files under
`relay-os/`, not hidden state. Suggested:
`relay-os/usage/ledger.jsonl` (append-only, one JSON record per session)
+ `relay-os/usage/summary.md` (rolled-up totals, the report surface).
Confirm the exact path/format during implement — it becomes a contract
the consumer tickets read, so keep records self-describing.

**Where capture hooks in (read this carefully).** `src/relay/commands/launch.py`
runs the agent via `run_with_done_marker` (interactive) or `subprocess.run`
(script/auto) around line 418–435 — but that call sits **inside a `while True:`
step-chaining loop** (≈lines 334–467). A single `relay launch` can spawn
**multiple** sessions in one process: implement → peer-review → open-pr,
rotating between claude and codex. So:

- Record **one ledger entry per loop iteration (per session)**, not one per
  launch. Each entry should carry slug, step, agent/CLI, and model — these
  differ across iterations within the same launch.
- Place capture in a `finally` around the subprocess call so a session that
  **burned tokens then exited non-zero** is still recorded. Note launch.py
  does `sys.exit(exit_code)` on non-zero exit (≈442–448) before the loop
  re-reads state — capture must run before that early exit, not after.
- A single supervised run can legitimately produce a **Codex** session, so the
  Codex stub must at minimum record a session with usage-unknown rather than
  crash or mis-attribute.

Keep the command entrypoint thin (per `relay/codebase`) — put the
parsing/rollup logic in a new module (e.g. `src/relay/usage.py`), not in
`launch.py`.

**Transcript source (Claude).** Claude Code writes per-message JSONL to
`~/.claude/projects/<cwd-hash>/<session-id>.jsonl`. Each assistant line
carries `usage` (`input_tokens`, `cache_creation_input_tokens`,
`cache_read_input_tokens`, `output_tokens`), `model`, and `sessionId`.
Cost is **not** in the transcript — derive it from `model` + a price
table. The four token categories are priced **differently** (cache-create
vs cache-read vs base input vs output), so the table needs per-category
rates, not one input price — Relay composes large cached context layers,
so cache tokens dominate and a single-rate approximation will be
materially wrong. Define the unknown-model behavior explicitly (record
tokens, cost-unknown — don't silently zero). Codex has its own transcript
format — implement Claude first and stub Codex behind a small provider
seam rather than hardcoding Claude assumptions everywhere.

**Transcript matching & double-counting (the likely-bug zone).** Don't
match transcripts by file mtime alone. The JSONL is append-only per
`sessionId`, so a resumed session's file contains prior turns' `usage`
lines — summing the whole file double-counts. Filter by **per-line
timestamp** within the session window (launch start → exit). Better still
if the spawned CLI's `sessionId` can be recovered (env/stdout/known path):
verify during implement whether claude/codex expose it to the parent —
launch.py does not capture it today. Also guard against a second
unrelated session open in the same cwd during the window.

**Robustness.** Capture must never break a launch. If the transcript
can't be found or parsed, still write a record with usage marked unknown
(and log it), rather than raising.

**Out of scope (separate tickets):** budget caps / "remaining" tokens,
autorouting decisions, the free-token opportunistic launcher, and wiring
totals into digest output. Build the primitive and the read command; let
the consumers consume.

**Tests / fixtures.** Add pytest coverage for the parser and rollup
(feed a synthetic transcript, assert the ledger record). Per CLAUDE.md,
update `example/` fixtures if launch/task layout semantics change.
Run `python -m pytest` and `relay validate --json` before the PR.
</content>
</invoke>
