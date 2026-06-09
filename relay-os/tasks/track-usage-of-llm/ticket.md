---
title: track usage of LLM
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
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

## Context

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
