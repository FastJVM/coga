---
slug: track-usage-of-llm
title: track usage of LLM
status: active
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/architecture
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
- After every `relay launch` *session* (one per `while True:` loop iteration
  in `launch.py`, not one per launch invocation), exactly one JSONL record is
  appended to the launched task's own `blackboard.md`, under a `## Usage`
  heading (created if absent). **There is no `relay-os/usage/` directory and no
  dedicated ledger file** — the task blackboards are the store.
  - Records are written for chained steps too (implement → peer-review →
    open-pr), each carrying its own `slug`, `step`, `agent`, `cli`, `model`.
  - A session that burned tokens and then exited non-zero is still recorded
    (capture runs in a `finally`, before launch.py's `sys.exit(exit_code)`).
  - Capture never raises into the launch path: any failure to find/parse a
    transcript appends a record with `usage_status: "unknown"` (tokens null),
    not an exception. A launch with **no task blackboard** (stateless bootstrap
    shims) is skipped silently — a known, accepted gap (see Out of Scope).
  - Append is safe: capture runs after the session subprocess has exited, so it
    never races the agent's own writes to that blackboard.
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
- A new recurring task `relay-os/recurring/refresh-hardcoded-data/` ships as
  part of this ticket: a twice-a-year sweep whose `blackboard.md` carries a
  `## Refresh` addendum (a checklist of hardcoded-data chores). When it fires
  it surfaces the addendum entries (one Slack reminder) so hardcoded data
  doesn't silently rot. This ticket seeds the addendum with a **real first
  entry**: "verify the Claude + Codex transcript parsers in `usage.py` still
  match the live `~/.claude` / `~/.codex` formats" — the parsers hardcode
  transcript paths and JSONL field names that drift when the CLIs update.
  Future tickets that hardcode data append one line here instead of each
  spawning their own recurring task. `relay validate --json` passes with it
  present.
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
  unknown path for either provider.
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

- **Claude** accepts `--session-id <uuid>`. In `build_agent_command`
  (launch.py), for the claude provider mint a `uuid4` per session and pass
  `--session-id <that>`, returning it to the loop so capture reads exactly that
  transcript file.
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
- Wrap the subprocess call's existing `try/finally` so that in the `finally`
  — after `_cleanup_prompt()`, before the `sys.exit(exit_code)` non-zero
  early return — it calls a single thin helper
  `usage.capture_session(...)` with the task's `blackboard` path, `title`,
  `slug`, `step` name, `agent`, `cli`, `provider`, `session_id`/`pre_existing`,
  `window_start`, `window_end=now`. The helper parses the transcript, builds the
  record, and appends one line under `## Usage` in that blackboard, swallowing
  all exceptions (log to stderr) so capture can never break a launch. If no
  blackboard path is available (stateless bootstrap shim), it no-ops.
- One record per loop iteration ⇒ chained steps and agent rotations each get
  their own entry, all appended to the same task blackboard.

**New command `src/relay/commands/usage.py`** registered in `cli.py` as
`relay usage`. Thin Typer entrypoint: options `--by`
(`task|model|agent|step`, **default `task`**), `--since`, `--until`, `--task`,
`--json`. Loads records via `usage.load_records` (which scans the blackboards),
calls `usage.rollup`, prints a table (human; the four token categories + total)
or `json.dumps` (machine). No parsing logic in the command.

**Recurring refresh-sweep (`relay-os/recurring/refresh-hardcoded-data/`).**
A new recurring task, modeled on the existing `digest` task (which already uses
its own `blackboard.md` `## Spool` section as the data surface its run reads).
Three files per the recurring `_template`:

- `ticket.md` — `schedule: "0 9 1 1,7 *"` (9am on Jan 1 and Jul 1 — twice a
  year), `schedule_comment` saying so. The run reads this task's own
  `blackboard.md` `## Refresh` section and posts one Slack reminder
  enumerating each chore that's due, so nothing hardcoded rots unnoticed.
- `blackboard.md` — carries a `## Refresh` addendum: a checklist where each
  entry is one hardcoded-data chore (`<file>` — what to verify — cadence).
  Seeded with one real entry: `src/relay/usage.py` — confirm the Claude and
  Codex transcript paths + JSONL field names still match the live formats.
  Future tickets append a line here.
- `log.md` — append-only run history (seed empty, like other recurring tasks).

Mode/workflow is an open design question (see blackboard): the lightest option
is `mode: auto` plus a tiny one-step `maintenance/refresh` workflow+skill that
reads the `## Refresh` section and posts a `relay slack` FYI — no new `relay`
subcommand. Recommend that over a `mode: script` command surface.

**Order of work:** (1) `usage.py` record + rollup + **both** parsers (Claude
per-message sum; Codex last-cumulative), with unit tests on synthetic
transcript fixtures for each, plus `append_record`/`load_records` round-trip
through a `## Usage` blackboard section. (2) `relay usage` command + tests.
(3) launch.py capture hook + per-provider matching (claude session-id minting;
codex pre-spawn rollout snapshot), appending to the task blackboard. (4) the
`refresh-hardcoded-data` recurring task (+ its `maintenance/refresh`
workflow/skill if that route is chosen). (5) `relay validate --json`, update
`example/` only if task/layout semantics change (they should not).

## Out of Scope

- Dollar cost / pricing — no price table, no `cost_usd`, no cost math. The team
  is on a subscription; tokens are the metric. A dollar view is a follow-up
  ticket if ever wanted.
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

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Open Questions — RESOLVED (2026-06-11, nick)

All six open questions answered. Spec updated to match.

1. **Price table** → **DROPPED entirely** (2026-06-11, nick: "ticket's big
   enough"). No price table, no `cost_usd` field, no cost math. Pricing is now
   in Out of Scope as a follow-up ticket. The ledger records tokens only; on a
   subscription, dollars aren't the metric.

   **BUT — the refresh-sweep mechanism stays, in this same ticket** (nick,
   2026-06-11). Instead of a dedicated per-concern recurring task, this ticket
   ships one **collated** recurring task `refresh-hardcoded-data/` whose
   `blackboard.md` carries a `## Refresh` addendum (checklist of hardcoded-data
   chores). It fires twice a year and surfaces the list. Seeded with the
   format + a commented example, **no pricing entry** (pricing's out of scope).
   When pricing eventually lands, that follow-up appends one line to the
   addendum rather than spawning its own recurring task. Mirrors the digest
   task's `## Spool`-as-data-surface pattern.

   Open: **mode/workflow for the sweep** — recommend `mode: auto` + a one-step
   `maintenance/refresh` workflow+skill that reads `## Refresh` and posts a
   `relay slack` FYI (no new `relay` subcommand). Alternative is a `mode:
   script` command. Decide at review-design / implement.
2. **summary regen** → every capture (default). Unchanged.
3. **Auto-commit** → no; leave write in working tree. Moved from open question
   to a settled decision in Out of Scope.
4. **Mint `claude --session-id`** → yes (internal mechanism, nick deferred to
   default).
5. **Codex stub** → fine, usage-unknown for now (default).
6. **Contexts** → added `relay/architecture` to `contexts:`.

## No dedicated ledger — store in task blackboards (2026-06-11, nick)

nick: "no need for a ledger, it can be parsed in the blackboard by the process
with a script (if we know title etc)." Dropped the whole `relay-os/usage/`
directory (ledger.jsonl + summary.md). New store:

- Capture appends one JSONL usage line to the **launched task's own**
  `blackboard.md` under a `## Usage` heading (digest-spool pattern). The launch
  process already knows title/slug/step/agent, so the line is self-describing.
- `relay usage` globs `tasks/**/blackboard.md` + `recurring/**/blackboard.md`,
  parses only valid JSON lines in each `## Usage` section, aggregates by
  title/slug/model/agent/step. It's the single read surface; no summary.md.
- `usage.py` surface changed: `append_record(blackboard, record)` (section
  append, atomic, touches only `## Usage`); `load_records(relay_os)` (scan
  blackboards); `rollup(...)`. Dropped `write_summary`.

**Accepted tradeoffs (chosen by nick over a central spool):**
1. Usage history is task-scoped — retiring/deleting a task dir drops its usage
   lines. Usage lives beside the work, not in a durable central ledger.
2. Stateless bootstrap shims (no persistent blackboard) aren't recorded —
   capture no-ops when there's no blackboard path. If it matters later, a
   central spool is the follow-up.

Append is race-free: capture runs in the `finally` after the session subprocess
has already exited, so the agent isn't concurrently writing that blackboard.

**Bonus:** this gives `refresh-hardcoded-data` a real first `## Refresh` entry —
the parsers hardcode transcript paths/field names that drift when the CLIs
update, so "verify usage.py parsers still match live formats" is the seeded
chore.

## Both providers parsed (2026-06-11, nick)

Codex is **not** stubbed — it's a first-class parser alongside Claude (nick:
"it's not claude only, it's for codex also"). Investigated the live
`~/.codex/sessions/` tree and confirmed it's fully parseable:

- Rollout file: `~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<ISO>-<uuid>.jsonl`.
- `session_meta` (line 1): `payload.id`, `payload.cwd`, `payload.model_provider`.
- `turn_context`: `payload.model` (e.g. `gpt-5.4`).
- `event_msg`→`token_count`: `info.total_token_usage` is **cumulative**
  (`input_tokens`, `cached_input_tokens`, `output_tokens`,
  `reasoning_output_tokens`, `total_tokens`) → take the LAST event, don't sum.
- Matching: `codex exec` has **no `--session-id`** (checked `codex exec --help`;
  it has `resume`, `--ephemeral`, `--json`, `-o`, but no id pin). So capture
  snapshots existing rollout files before spawn and the parser claims the NEW
  file with matching `session_meta.cwd`. Robust, no double-count (cumulative).
- Category mapping → shared 4-field record: cached_input→cache_read, reasoning
  folded into output, cache_create→null (codex exposes no create/read split).

Claude keeps the minted `--session-id` strategy. Both have deterministic,
non-mtime matching now.

**Key reframe from nick:** the team is on a **Claude subscription**, not
per-token API billing. So the headline metric is **tokens per task**, not
dollars. Spec now leads `relay usage` and `summary.md` with tokens-by-task
(`--by` defaults to `task`); `cost_usd` is a secondary informational column
that degrades to `—`/`null` for unpriced models without harming token
reporting. Added a "Primary metric" paragraph to the Description.

## Bootstrap decisions (2026-06-09, interactive with nick)

- **Scope:** ledger primitive only. Capture + store + `relay usage` read command.
  Budget caps / "remaining" / autorouting / free-token launcher / digest wiring
  are out of scope — separate consumer tickets (one exists:
  `autoroute-agent-based-on-remaining-usage`).
- **Capture mechanism:** parse agent transcripts after the session returns
  (launches inherit the terminal, so usage can't be streamed). Claude first,
  Codex stubbed behind a provider seam.
- **Budget cap:** deferred. This ticket records spend only; "remaining" is a
  consumer's problem.
- **Workflow:** `code/design-then-implement`. Nick chose the design-gate
  variant over `code/with-review` because the ledger schema + `relay usage`
  signature are a contract the downstream tickets read — the design step
  pins them and the owner reviews the spec before any code is written.

## Evaluator review

I have enough grounding. Let me note the key mismatch I found between the ticket's claims and the actual launch.py code, then give the assessment.

Key verification finding: the ticket says capture hooks in "after the agent exits ... around line 418–435" via `run_with_done_marker` / `subprocess.run`. But that block is **inside a `while True:` per-step chaining loop** (lines 334–467). A single `relay launch` invocation can spawn **multiple** agent sessions (implement → peer-review → open-pr, rotating claude↔codex) within one process. This materially affects the design and the ticket understates it.

Assessment below.

---

1. Clarity for a cold-start agent — mostly yes, with gaps

- The three-part Capture/Store/Read structure is clear and the intent ("foundational primitive, consumers are separate tickets") is well-stated. An agent could begin.
- Concrete grounding is good: exact transcript path, the `usage` field names, the "put logic in `src/relay/usage.py`, keep `launch.py` thin" steer (correctly matches `relay/codebase`).
- Gap: the `relay usage` command surface is underspecified. "totals... overall, by task, by model, by window" — but "window" is undefined (time window? session? what granularity?), and there's no example output, no flag shape, no machine vs human output contract. The accessor is explicitly the contract for 3 downstream tickets, yet its interface is the least specified part.
- Gap: "derived cost" leans on "a small price table (Claude pricing)" with no source-of-truth named and no statement of what happens when a model id isn't in the table (silent zero? unknown? same as the transcript-missing path?).

2. Workflow fit — code/with-review is reasonable, but a design gate is warranted

- The work is genuinely a code change with testable parser/rollup logic, so code/with-review (implement → peer-review → open-pr → human review) fits the *mechanics*.
- However, the ticket itself flags three things that become contracts for other tickets: the ledger record schema, the file path/format, and the `relay usage` accessor signature. It defers all of them to "confirm during implement." With this workflow the first time a human sees those decisions is the final PR review — after the peer agent has already built on them. For a primitive whose whole justification is "3 consumers read this," an explicit design/spec checkpoint before implementation would de-risk it. There is no design-review gate in code/with-review (peer-review is a code diff review, not a schema sign-off). This is the most defensible criticism: the format-as-contract nature argues for a lighter-weight schema agreement up front, or splitting a "design the ledger record + usage interface" step out.

3. Contexts — relay/codebase is correct but insufficient; relay/architecture is needed

- relay/codebase is the right attach (it's the "editing relay's own code" context and gives source layout + test/validate commands). Good.
- relay/architecture is missing and the ticket arguably **needs** it: the Context section makes architectural claims ("no database, no daemon," "plain committed files, not hidden state," append-only ledger under `relay-os/`) and attributes them to `relay/architecture` — but that context isn't attached, so the agent picking this up won't actually have read the primitive model it's being told to respect. Either attach `relay/architecture` or drop the parenthetical that implies it was consulted.
- relay/principles would also help (the "legible, no hidden state" non-negotiable is a principle), though architecture is the higher-value add.

4. Scope — borderline; defensible as one ticket but on the heavy side

- The ticket explicitly fences out budgets/remaining/autoroute/free-token-launcher/digest-wiring, which is good discipline and keeps it as a primitive.
- What remains is still three non-trivial pieces: (a) a transcript parser with a provider seam (Claude now, Codex stubbed), (b) the launch.py capture hook with robustness/no-double-count logic, and (c) a new `relay usage` read command with multiple aggregation axes. (a)+(b) are the real primitive; (c) is a separate command surface that could be its own ticket. It doesn't bundle a *consumer's* worth of work, but it's two deliverables (write-path + read-path) wearing one ticket. Acceptable, but if velocity matters, splitting capture/store from the `usage` command would each be cleaner and independently reviewable.

5. Assumptions to question before launch

- **Multi-session per launch (most important).** The ticket says write "one record per session" after the agent exits "around line 418–435," implying one capture per launch. In reality that block sits inside a `while True:` chaining loop (launch.py 334–467): a single launch can run implement, then rotate to the peer agent for peer-review, then back for open-pr — multiple sessions, multiple transcripts, possibly two different models/CLIs, in one process. Capture must run **once per loop iteration (per session)**, not once per launch, and must handle the claude↔codex rotation. The ticket's "stub Codex" plan collides with this: a single supervised run can legitimately produce a Codex session that the Claude-only parser can't read. This needs to be called out before launch.
- **Session-id / transcript matching.** "Identify transcript(s) by the session window (launch start → exit) for the launch cwd" is fragile. launch.py does not currently capture or surface the agent's session id; matching purely by mtime-window + cwd-hash will mis-attribute when (a) the user has another Claude session open in the same cwd, or (b) the agent resumes/continues an existing session file (the JSONL appends rather than creating a new file). The robust signal is the `sessionId` in the JSONL, but relay would need to *know* which session id the spawned CLI used — it currently doesn't. Worth verifying whether claude/codex expose the session id to the parent (env, stdout, or a known path) before committing to window-matching.
- **Double-counting on resume.** Directly related: because transcripts are append-only per session file, a resumed session's JSONL contains prior turns' `usage` lines. Window-filtering by line timestamp (not file mtime) is required, and the ticket waves at this ("be careful not to double-count") without prescribing the mechanism. This is the single most likely correctness bug and deserves a concrete strategy in the ticket.
- **Cache-token cost semantics.** The transcript splits `cache_creation_input_tokens` and `cache_read_input_tokens`, which are priced differently from base input tokens. "derive cost from model + a small price table" understates this — the price table needs per-category rates, not one input price, or the cost column will be materially wrong for cache-heavy Relay prompts (which compose large context layers, so cache usage will be high).
- **Robustness path interaction with the freshness check / exit codes.** launch.py `sys.exit(exit_code)` on non-zero agent exit (line 442–448) returns before the loop re-reads state. Where capture sits relative to that early exit matters: a crashed/non-zero session would be skipped entirely unless capture runs in the `finally` around the subprocess call. The ticket says "must never break a launch" but doesn't address the non-zero-exit early-return, where a session that burned tokens then errored would silently produce no record.

Relevant files: ticket at `/home/n/Code/relay/relay-os/tasks/track-usage-of-llm/ticket.md`; capture hook reality at `/home/n/Code/relay/src/relay/commands/launch.py` (the `while True:` loop, lines 334–467, and the non-zero-exit early return at 442–448); workflow at `/home/n/Code/relay/relay-os/workflows/code/with-review.md` (no design gate; peer-review is a diff review).

## Design step (2026-06-09, claude)

Spec written into ticket.md: Acceptance Criteria, Proposed Shape, Out of Scope.
The evaluator's five risks are now all addressed in the spec:

1. **Multi-session per launch** — spec mandates one record per `while True:`
   loop iteration, each carrying its own slug/step/agent/cli/model; covers
   the claude↔codex rotation explicitly.
2. **Transcript matching** — *resolved by a new finding*: `claude` accepts
   `--session-id <uuid>`. launch.py mints a uuid4 per claude session, passes
   it, and reads exactly `~/.claude/projects/<cwd-hash>/<uuid>.jsonl`.
   Deterministic lookup, no mtime/window heuristic. Verified the path layout
   against the live `~/.claude/projects/-home-n-Code-relay/` dir and confirmed
   assistant lines carry `timestamp`, `sessionId`, `message.model`,
   `message.usage.{input,cache_creation_input,cache_read_input,output}_tokens`.
3. **Double-counting** — minted-session file is session-scoped, so summing it
   is safe; per-line `timestamp` window filter kept as a defensive guard and as
   the fallback when session-id is unknown (codex / older claude).
4. **Cache-token cost** — spec requires a per-category price table (4 rates),
   not a single input rate.
5. **Non-zero-exit early return** — capture runs in the `finally` around the
   subprocess call, before launch.py's `sys.exit(exit_code)`.

## Open Questions (for review-design)

1. **Price table source of truth.** Recommend a hardcoded `PRICES` dict in
   `usage.py` with an "as of <date>" comment + unknown-model → `cost_usd: null`.
   Alternative: put rates in `relay.toml` so they're editable without a code
   change. Hardcoded is simpler and keeps the contract in one place; config-
   driven survives price changes without a PR. Which do you want? (Default:
   hardcoded.)

2. **summary.md regeneration cadence.** Recommend regenerating on every capture
   so the committed file is always current. Tradeoff: noisier git diffs (a line
   changes on every launch). Alternative: only regenerate on
   `relay usage --write-summary`. (Default: on every capture.)

3. **Does capture auto-commit the ledger?** Currently launch.py commits nothing;
   the ledger write would sit in the working tree for the next commit to pick
   up. Auto-committing per session is possible but adds git side effects to
   `relay launch`. (Default: no auto-commit — leave it to normal flow. Listed in
   Out of Scope.)

4. **Minting `claude --session-id`.** This changes the spawned command (relay
   dictates the session id instead of letting claude generate one). Low risk and
   it's the cleanest matching strategy, but confirm you're OK with relay owning
   the session id. (Default: yes, mint it.)

5. **Codex stub acceptability.** A supervised run that rotates to codex will
   produce a `usage_status: "unknown"` record this ticket. Confirm that's an
   acceptable interim state vs. blocking on a real codex parser. (Default: stub
   is fine — full codex parser is a follow-up.)

6. **Contexts.** Evaluator suggested attaching `relay/architecture` (and maybe
   `relay/principles`) since the spec leans on the "no hidden state, plain
   committed files" model. Want me to add `relay/architecture` to `contexts:`
   before implement? (Default: add it — the implementer should read the
   primitive model it's told to respect.)

